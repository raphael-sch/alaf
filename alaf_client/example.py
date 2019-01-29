from alaf_client.datasets import get_dataset
from alaf_client.svm_al_model import LeastConfidenceALModel

data_dir = './data/SST2/'
model = LeastConfidenceALModel(dataset_func=lambda: get_dataset(data_dir),
                               output_dir='./models/',
                               project_name='project3',
                               name='model_least',
                               host='alaf.tech-demos.de',
                               port=80,
                               n_jobs=-1,
                               baseline=False)
