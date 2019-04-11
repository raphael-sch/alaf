import argparse
from example import LeastConfidenceALModel, RandomALModel, get_dataset


# python cmd.py -project project1 -name model1 -host localhost -port 5000 -model svm_random -data_dir ./data/example/ -output_dir ./models/

def start(project_name, name, host, port, model_cls, data_dir, output_dir, simulation=False, batch_size=1024, n_jobs=-1):

    model_cls(dataset_func=lambda: get_dataset(data_dir),
              output_dir=output_dir,
              project_name=project_name,
              name=name,
              host=host,
              port=port,
              simulation=simulation,
              batch_size=batch_size,
              n_jobs=n_jobs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run alaf client')

    parser.add_argument('-project', type=str,
                        help='Project name')

    parser.add_argument('-name', type=str,
                        help='Model/Client name')

    parser.add_argument('-host', type=str, default='localhost',
                        help='Host ip/url')

    parser.add_argument('-port', type=int, default=5000,
                        help='Port of host')

    parser.add_argument('-model', type=str,
                        help='svm_random or svm_least')

    parser.add_argument('-data_dir', type=str,
                        help='Path to data directory')

    parser.add_argument('-output_dir', type=str,
                        help='Path to output folder')

    parser.add_argument('-simulation', type=bool,
                        help='Simulation mode needs pool_label.txt file. Remove this flag completely for no simulation'
                             ' mode (do not just set it to False)')

    parser.add_argument('-batch_size', type=int, default=1024,
                        help='batch size for multiprocess dataset handling')

    parser.add_argument('-n_jobs', type=int, default=-1,
                        help='number of parallel processes.')

    args = parser.parse_args()
    model = None
    if args.model == 'svm_random':
        model = RandomALModel
    elif args.model == 'svm_least':
        model = LeastConfidenceALModel

    start(args.project,
          args.name,
          args.host,
          args.port,
          model,
          args.data_dir,
          args.output_dir,
          args.simulation,
          args.batch_size,
          args.n_jobs)
