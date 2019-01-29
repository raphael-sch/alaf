from sklearn.feature_extraction.text import CountVectorizer
import fileinput
import os


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
