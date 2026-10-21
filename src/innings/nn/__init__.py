"""The neural network: one model that has read every ball of cricket we hold.

    features.py   what the network is shown for one ball, and how a ball becomes numbers
    data.py       the balls from the database, turned into arrays, split by time
    model.py      the network itself (PyTorch)
    train.py      training, baselines, the honest test, and the exported artefacts
    serve.py      running the exported model with onnxruntime, without PyTorch

Training needs the `train` extra (PyTorch, on a GPU). The site needs only `serve.py`.
"""
