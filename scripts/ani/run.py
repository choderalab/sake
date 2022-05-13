import jax
import jax.numpy as jnp
import numpy as onp

class Collater(object):
    def __init__(self, ds_tr, batch_size=128):
        self.ds_tr = ds_tr
        self.batch_size = batch_size
        self.pointers = []

    def _move_to_device(ds_tr):
        for length in ds_tr:
            ds_tr[length]['i'] = jnp.array(ds_tr[length]['i'])
            ds_tr[length]['x'] = jnp.array(ds_tr[length]['x'])
            ds_tr[length]['y'] = jnp.array(ds_tr[length]['y'])
        return ds_tr

    def get_pointers(self):
        pointers = []
        for length in self.ds_tr:
            n_data = self.ds_tr[length]['x'].shape[0]
            n_batches = int(n_data / self.batch_size)
            idxs = onp.random.permutation(n_data)[:n_batches*self.batch_size]
            idxs = idxs.reshape(n_batches, self.batch_size)
            for idx in idxs:
                pointers.append((length, idx))
        import random
        random.shuffle(pointers)
        self.pointers = pointers
        return pointers

    def get_from_pointer(self, pointer):
        length, idxs = pointer
        return (
                jax.nn.one_hot(self.ds_tr[length]['i'][idxs], 4),
                jnp.array(self.ds_tr[length]['x'][idxs]),
                jnp.expand_dims(jnp.array(self.ds_tr[length]['y'][idxs]), -1),
        )

    def __iter__(self):
        self.get_pointers()
        return self

    def __next__(self):
        if len(self.pointers) == 0:
            raise StopIteration
        else:
            pointer = self.pointers.pop()
            return self.get_from_pointer(pointer)


def run():
    # data = ANIDataset()
    ds_tr = onp.load("ds_tr.npy", allow_pickle=True)[()]
    collater = Collater(ds_tr)

    import sake
    model = sake.models.DenseSAKEModel(
        hidden_features=64,
        out_features=1,
        depth=8,
    )

    def get_y_pred(params, i, x):
        y_pred, _, __ = model.apply(params, i, x)
        y_pred = y_pred.sum(axis=-2)
        return y_pred

    def get_loss(params, i, x, y):
        y_pred = get_y_pred(params,i, x)
        loss = jnp.abs(y_pred - y).mean()
        return loss

    i, x, y = next(iter(collater))
    print(i.shape, x.shape, y.shape)
    params = model.init(jax.random.PRNGKey(2666), i, x)

    import optax
    optimizer = optax.chain(
        optax.additive_weight_decay(1e-12),
        optax.clip(1.0),
        optax.adam(1e-5),
    )

    from flax.training.train_state import TrainState
    from flax.training.checkpoints import save_checkpoint

    state = TrainState.create(
        apply_fn=model.apply, params=params, tx=optimizer,
    )



    @jax.jit
    def step(state, i, x, y):
        params = state.params
        loss, grads = jax.value_and_grad(get_loss)(params, i, x, y)
        state = state.apply_gradients(grads=grads)
        return loss, state

    from tqdm import tqdm
    for idx_batch in tqdm(range(50)):
        for i, x, y in collater:
            loss, state = step(state, i, x, y)
        save_checkpoint("_checkpoint", target=state, step=idx_batch)



if __name__ == "__main__":
    run()
