# ALAF: Active Learning Annotation Framework
## Server
### Requirements
- Python 3.6
- SQLite

    pip install -r requirements.txt
    
    #if sqlite not installed:
    sudo apt-get install sqlite
### Prepare
    # update secret keys in config.py
    python install.py
### Run
    python run.py
    #open host:port (e.g. http://localhost:5000 in browser)
    
## Client
### Requirements
- Python 3.6


    pip install -r requirements.txt
    #The svm example models need sklearn:
    pip install scikit-learn
### Prepare
- start server
### Run
    python cmd.py -project project1 -name model1 -host localhost -port 5000 -model svm_random -data_dir ./data/example/ -output_dir ./models/
