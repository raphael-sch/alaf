from alaf_client.base import BaseALModel

from sklearn.feature_extraction.text import CountVectorizer
import fileinput
from sklearn.svm import SVC
from sklearn.metrics import precision_score, recall_score, f1_score
from scipy.sparse import vstack
import os
from random import choice
import multiprocessing as mp


class SvmALModel(BaseALModel):

    def __init__(self, dataset_func,
                 output_dir,
                 project_name,
                 name,
                 host='localhost',
                 port=5000,
                 simulation=False,
                 batch_size=1024,
                 n_jobs=-1):
        """
        Base class for SVM based active learning methods. Handles the SVM model and training and newly
        annotated instances.
        :param dataset_func: Construct the dataset
        :param output_dir: output folder
        :param project_name: project name
        :param name: model name
        :param host: host ip/url
        :param port: port of host
        :param simulation: simulation mode
        :param batch_size: batch size for multiprocess dataset handling
        :param n_jobs: number of parallel processes
        """
        self.output_dir = output_dir
        self.batch_size = batch_size

        project_model_name = '{}.{}'.format(project_name, name)
        self.model_dir = os.path.join(self.output_dir, project_model_name)
        os.makedirs(self.model_dir, exist_ok=True)

        self.dataset = dataset_func()
        self.alaf_file = os.path.join(self.model_dir, 'alaf.txt')
        self.alaf_annotation_file = os.path.join(self.model_dir, 'alaf_annotation.txt')
        with open(self.alaf_file, 'a'):
            pass
        with open(self.alaf_annotation_file, 'a'):
            pass

        alaf_lines = [l.rstrip() for l in open(self.alaf_file).readlines()]
        x_alaf = self.dataset['vectorizer'].transform(alaf_lines)
        y_alaf = [int(l.rstrip()) for l in open(self.alaf_annotation_file).readlines()]
        self.alaf_lines = set(alaf_lines)

        self.dataset.update(dict(x_alaf=x_alaf, y_alaf=y_alaf))

        self.count = len(self.dataset['y_alaf'])
        self.trained_model = self.get_ml_model()

        self.n_jobs = n_jobs if n_jobs > 0 else mp.cpu_count()
        self.mp_pool = mp.Pool(n_jobs if n_jobs > 0 else mp.cpu_count())

        super(SvmALModel, self).__init__(project_name=project_name,
                                         name=name,
                                         host=host,
                                         port=port,
                                         simulation=simulation)

    def add_instance(self, utterance, annotation):
        """
        Handles the new instance received from the server. Transforms text to vector and adds it to
        the training instances.
        :param utterance: text
        :param annotation: human annotation
        :return:
        """
        vectorizer = self.dataset['vectorizer']
        x_utterance = vectorizer.transform([utterance])
        if self.get_count() == 0:
            self.dataset['x_alaf'] = x_utterance
            self.dataset['y_alaf'] = [annotation]
        else:
            self.dataset['x_alaf'] = vstack([self.dataset['x_alaf'], x_utterance])
            self.dataset['y_alaf'] += [annotation]

        with open(self.alaf_file, 'a') as f:
            f.write(utterance + '\n')
        self.alaf_lines.add(utterance)
        with open(self.alaf_annotation_file, 'a') as f:
            f.write(str(annotation) + '\n')

        self.count += 1
        self.trained_model = self.get_ml_model()

    def get_ml_model(self):
        """
        Instantiate and train SVM with all available training data.
        :return: trained SVM
        """
        ml_model = SVC(kernel='linear', probability=True)
        x_train, y_train = self.dataset['x_train'], self.dataset['y_train']

        if self.get_count() > 0:
            x_alaf, y_alaf = self.dataset['x_alaf'], self.dataset['y_alaf']
            x_train = vstack([x_train, x_alaf])
            y_train = y_train + y_alaf

        ml_model.fit(x_train, y_train)
        return ml_model

    def get_scores(self):
        """
        Get scores of SVM on test set.
        :return: precision, recall, f1
        """
        x_test, y_test = self.dataset['x_test'], self.dataset['y_test']

        y_pred = self.trained_model.predict(x_test)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)

        return precision, recall, f1

    def get_next_utterance(self, prev_annotation=None):
        """
        Override this with actual active learning algorithm
        :return: utterance
        """
        raise NotImplementedError

    def get_count(self):
        """
        Return count property
        :return: current number of added training instances
        """
        return self.count


class LeastConfidenceALModel(SvmALModel):

    def __init__(self, *args, **kwargs):
        """
        Select utterance with lowest confidence from the active learning pool.
        :param args:
        :param kwargs:
        """
        super(LeastConfidenceALModel, self).__init__(*args, **kwargs)

    @staticmethod
    def _get_next_utterance_mp(args):
        """
        Started in a own process. Works on a slice of the whole pool file and returns the local least
        confident utterance together with its confidence score.
        :param args:
        :return: utterance, confidence, label
        """
        ml_model, alaf_lines, pool_file, offsets, vectorizer, pool_labels, start, end = args

        ml_model.confidence = lambda x: [max(v) for v in ml_model.predict_proba(x)]

        lines_pool = list()
        # jump into file based on offset this process is working on
        with open(pool_file) as f:
            f.seek(offsets[start])
            for i, line in enumerate(f):
                lines_pool.append(line.rstrip())
                if i+start == end:
                    break

        x_pool = vectorizer.transform(lines_pool)
        confidence = None
        idx = None

        confs = ml_model.confidence(x_pool)
        for i, c in enumerate(confs):
            # check if current line idx has lowest confidence and if the line has not already been selected
            if (idx is None or c < confidence) and lines_pool[i] not in alaf_lines:
                confidence = c
                idx = i

        if idx is None:
            raise ValueError('no unseen pool instances left')
        utterance = lines_pool[idx]
        label = pool_labels[idx + start] if pool_labels else None

        return utterance, confidence, label

    def get_next_utterance(self, prev_annotation=None):
        """
        Separates the pool file into smaller chunks and sent them to different processes.
        Find the utterance with the lowest confidence score across the whole pool file.
        :return: utterance, label/None
        """

        # create start and end line idx for portion of pool file each process handles
        inp = len(self.dataset['pool_file_offsets'])
        n = self.batch_size
        chunks = [(i, min(i+n-1, inp-1)) for i in range(0, inp, n)]

        args = [(self.trained_model,
                 self.alaf_lines,
                 self.dataset['pool_file'],
                 self.dataset['pool_file_offsets'],
                 self.dataset['vectorizer'],
                 self.dataset.get('pool_labels'),  # default None
                 start,
                 end)
                for start, end in chunks]
        results = self.mp_pool.map(LeastConfidenceALModel._get_next_utterance_mp, args)
        utterance, _, label = sorted(results, key=lambda e: e[1])[0]

        return utterance, label


class RandomALModel(SvmALModel):

    def __init__(self, *args, **kwargs):
        """
        Randomly selects an utterance from the pool file.
        :param args:
        :param kwargs:
        """
        super(RandomALModel, self).__init__(*args, **kwargs)

    def get_next_utterance(self, prev_annotation=None):
        """
        Read an utterance from the pool file by randomly selecting a line start position.
        :return: utterance, label
        """
        utterance = None
        while utterance is None or utterance in self.alaf_lines:
            idx = choice(range(len(self.dataset['pool_file_offsets'])))
            offset = self.dataset['pool_file_offsets'][idx]
            with open(self.dataset['pool_file']) as f:
                f.seek(offset)
                line = f.readline()
            utterance = line.rstrip()

        label = None
        if 'pool_labels' in self.dataset:
            label = self.dataset['pool_labels'][idx]

        return utterance, label


def get_dataset(data_dir):
    """
    Read dataset from provided data_dir. One line per utterance and one label per line in a separate file
    for train, dev, test and (both if possible) pool. Named x.txt and x_label.txt
    Features are extracted as one-hot vectors representing uni grams.
    :param data_dir: path to data folder like SST-2
    :return: dict with train, dev, test, pool data and feature extractor
    """
    print('load dataset from: {}'.format(data_dir))
    train_file = os.path.join(data_dir, 'train.txt')
    train_label_file = os.path.join(data_dir, 'train_label.txt')
    dev_file = os.path.join(data_dir, 'dev.txt')
    dev_label_file = os.path.join(data_dir, 'dev_label.txt')
    test_file = os.path.join(data_dir, 'test.txt')
    test_label_file = os.path.join(data_dir, 'test_label.txt')

    pool_file = os.path.join(data_dir, 'pool.txt')
    pool_label_file = os.path.join(data_dir, 'pool_label.txt')

    vectorizer = CountVectorizer()
    vectorizer.fit(fileinput.input([train_file, pool_file]))

    def get_labels(filename):
        return [int(l.rstrip('/n')) for l in open(filename).readlines()]

    x_train = vectorizer.transform(open(train_file))
    y_train = get_labels(train_label_file)
    x_dev = vectorizer.transform(open(dev_file))
    y_dev = get_labels(dev_label_file)
    x_test = vectorizer.transform(open(test_file))
    y_test = get_labels(test_label_file)

    # needed for efficient file navigation
    pool_file_offsets = []
    offset = 0
    with open(pool_file, 'rb') as f:
        for line in f:
            pool_file_offsets.append(offset)
            offset += len(line)

    dataset = dict(vectorizer=vectorizer,
                   x_train=x_train, y_train=y_train,
                   x_dev=x_dev, y_dev=y_dev,
                   x_test=x_test, y_test=y_test,
                   pool_file=pool_file,
                   pool_file_offsets=pool_file_offsets
                   )

    if pool_label_file is not None:
        pool_labels = get_labels(pool_label_file)
        dataset['pool_labels'] = pool_labels

    return dataset


if __name__ == '__main__':
    data_dir = './data/example/'
    model = LeastConfidenceALModel(dataset_func=lambda: get_dataset(data_dir),
                                   output_dir='./models/',
                                   project_name='project1',
                                   name='model1',
                                   host='localhost',
                                   port=5000,
                                   n_jobs=-1,
                                   simulation=False)
