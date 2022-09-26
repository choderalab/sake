import lmdb
import pickle
import numpy as np

def run():
    data = {}
    path = "is2res_train_val_test_lmdbs/data/is2re/10k/train/data.lmdb"
    env = lmdb.open(
        path,
        subdir=False,
        readonly=True,
        lock=False,
    )
    length = env.stat()["entries"]
    keys = [f"{j}".encode("ascii") for j in range(env.stat()["entries"])]
    txn = env.begin()

    for key in keys:
        _data = pickle.loads(txn.get(key)).__dict__
        x = _data["pos"].numpy()
        y = _data["y_relaxed"]
        i = _data["atomic_numbers"].numpy()
        i = np.repeat(np.expand_dims(i, 0), x.shape[0], 0)
        length = x.shape[1]
        if length in data:
            data[length]['i'].append(i)
            data[length]['x'].append(x)
            data[length]['y'].append(y)
        else:
            data[length] = {'i': [i], 'x': [x], 'y': [y]}

    for length in data:
        data[length] = np.array(data[length])

    np.save("is2re10k.npy", data)

if __name__ == "__main__":
    run()
