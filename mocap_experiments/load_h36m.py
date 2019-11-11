import pickle
import numpy as np
import random
import collections
PoseData = collections.namedtuple('PoseData', ['f', 'action', 'actor', 'array'])
H36M_USED_JOINTS = [0, 1, 2, 3, 6, 7, 8, 12, 13, 14, 15, 17, 18, 19, 25, 26, 27]


class H36MDataSet(object):
    """
    Create a Human 3.6M data set based on the output created by human36M_pickle_skeletons.py
    """
    def __init__(self, train=True, chunk_size=100, dataset_name='h36m'):
        print('train set', train)
        self.train = train
        if train:
            train_file = '/home/moritz/uni/fourier-prediction/mocap_experiments/data/un_zipped/by_actor/train_' + dataset_name + '.pkl'
            # train_file = '/home/wolter/fourier-pred-tmp/mocap_experiments/data/un_zipped/by_actor/train_' + dataset_name + '.pkl'
            print('opening', train_file)
            self.data = pickle.load(open(train_file, 'rb'))
        else:
            val_file = '/home/moritz/uni/fourier-prediction/mocap_experiments/data/un_zipped/by_actor/val_' + dataset_name + '.pkl'
            # val_file = '/home/wolter/fourier-pred-tmp/mocap_experiments/data/un_zipped/by_actor/val_' + dataset_name + '.pkl'
            print('opening', val_file)
            self.data = pickle.load(open(val_file, 'rb'))

        self.chunk_size = chunk_size
        self.data_array = self._pre_process()
        self.mean, self.std = self.get_mean_and_std()

    def get_mean_and_std(self):
        mean = np.mean(self.data_array)
        std = np.std(self.data_array)
        return mean, std

    def _pre_process(self, start_at=0):
        """
        A random offset to avoid training and testing on all the same chunks all the time.
        :return: A numpy array with data batches arranged as [batches, time, joints, 3d_points]
        """
        data_chunks = []
        lost_total = 0
        for data_el in self.data:
            data_array = data_el[-1][H36M_USED_JOINTS, :, :]
            time_total = data_array.shape[-1] - start_at
            chunks = time_total//self.chunk_size
            stop_at = chunks*self.chunk_size + start_at
            lost = time_total - stop_at
            lost_total += lost
            np_splits = np.array_split(data_array[:, :, start_at:stop_at], chunks, axis=-1)
            data_chunks.extend(np_splits)
            # print('processing element', data_el[0], data_el[1], data_el[2], 'lost frames', lost, 'total', lost_total)
        print('preprocessing done, offset', start_at)
        data_array = np.stack(data_chunks, axis=-1)
        return np.transpose(data_array, [3, 2, 0, 1])

    def get_batches(self):
        """
        Get human 3.6M mocap squences in temporal chunks.
        :return: [batch_total, chunk_size, 17, 3]
        """
        if self.train:
            np.random.shuffle(self.data_array)
            to_return = self.data_array
            self.data_array = self._pre_process(start_at=int(np.random.uniform(0, self.chunk_size)))
        else:
            to_return = self.data_array
        # print('train', self.train, 'set size', len(self.data_array))
        return to_return


if __name__ == "__main__":
    import tensorflow as tf
    import matplotlib.pyplot as plt
    import scipy.signal as scisig
    from mocap_experiments.write_movie import write_movie
    from eager_STFT import stft, istft
    time = False

    try:
        tf.enable_eager_execution()
    except ValueError:
        print("tensorflow is already in eager mode.")

    data = H36MDataSet(chunk_size=128)
    batches = data.get_batches()
    batches = data.get_batches()
    if time:
        write_movie(np.transpose(batches[0], [1, 2, 0]), 'sample_batch.mp4')
        batches = batches - data.mean
        batches = batches/data.std
        write_movie(np.transpose(batches[0], [1, 2, 0]), 'sample_batch_norm.mp4', r_base=1000/data.std)
        print('written')
    else:
        batches = batches - data.mean
        batches = batches/data.std
        window_size = 8
        overlap = int(window_size*0.5)
        window = tf.constant(scisig.get_window('hann', window_size),
                             dtype=tf.float32)
        # test fft.
        shape = batches.shape
        rs_batches = np.reshape(batches, [shape[0], shape[1], shape[2]*shape[3]])
        time_last_batches = np.moveaxis(rs_batches, [0, 1, 2], [0, 2, 1])
        time_last_batches = tf.constant(time_last_batches)
        freq_batches = stft(time_last_batches, window, window_size, overlap, padded=True)
        time_data = istft(freq_batches, window, nperseg=window_size, noverlap=overlap, epsilon=0.01)
        dimensions_last = np.moveaxis(time_data.numpy(), [0, 1, 2], [0, 2, 1])
        np_time_data = np.reshape(dimensions_last, shape)
        write_movie(np.transpose(np_time_data[0], [1, 2, 0]), 'fft_sample_batch_norm.mp4', r_base=1000/data.std)
        error = np.linalg.norm((batches[0] - np_time_data[0]).flatten())
        print('done, error:', error)
