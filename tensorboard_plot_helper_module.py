"""
A helper module meant to facilitate extracting nicer looking
plots from tensorboard.
"""

import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import os
from IPython.core.debugger import Pdb
debug_here = Pdb().set_trace


def tensoboard_average(y, window):
    '''
    * The smoothing algorithm is a simple moving average, which, given a
     * point p and a window w, replaces p with a simple average of the
     * points in the [p - floor(w/2), p + floor(w/2)] range.
    '''
    window_vals = []
    length = y.shape[-1]
    for p_no in range(0, length, window):
        if p_no > window/2 and p_no < length - window/2:
            window_vals.append(np.mean(y[p_no-int(window/2):p_no+int(window/2)]))
    return np.array(window_vals)


def plot_logs(ps, legend, title, window_size=25, vtag='mse', ylim=[0.00, 0.35],
              tikz=False, pdf=False, filename='tfplots.tex', log=False):
    # cs = ['b', 'r', 'g']
    for no, p in enumerate(ps):
        adding_umc = []
        try:
            for e in tf.train.summary_iterator(p):
                for v in e.summary.value:
                    if v.tag == vtag:
                        # print(v.simple_value)
                        adding_umc.append(v.simple_value)
        except:
            # ingnore that silly data loss error....
            pass
        # x = np.array(range(len(adding_umc)))

        y = np.array(adding_umc)
        yhat = tensoboard_average(y, window_size)
        xhat = np.linspace(0, y.shape[0], yhat.shape[0])
        # plt.plot(yhat, cs[no])
        if log:
            plt.semilogy(xhat, yhat, label=legend[no])
        else:
            plt.plot(xhat, yhat, label=legend[no])

    plt.ylim(ylim[0], ylim[1])
    plt.grid()
    plt.ylabel(vtag)
    plt.xlabel('updates')
    plt.legend()
    plt.title(title)

    if tikz:
        from matplotlib2tikz import save as tikz_save
        tikz_save(filename)
    elif pdf:
        plt.savefig(filename, bbox_inches='tight')
    else:
        plt.show()


def return_logs(path, window_size=25, vtag='mse', filter_str=None):
    """
    Load loss values from logfiles smooth and return.
    Params:
        path: The path to a folder, where mutliple experiment runs are stored
              in subdirectories.
        window_size: The size of the window used for the mean-curve-smoothing.
        vtag: The plot title in tensorboard.
    """
    file_lst = []
    for root, dirs, files in os.walk(path):
        if not root.split('/')[-1] == 'weights':
            print(dirs)
            print(files)
            for file in files:
                if file.split('.')[0] == 'events':
                    file_lst.append(os.path.join(root, file))
    xy_lst = []
    for no, p in enumerate(file_lst):
        adding_umc = []
        try:
            for e in tf.train.summary_iterator(p):
                for v in e.summary.value:
                    if v.tag == vtag:
                        # print(v.simple_value)
                        adding_umc.append(v.simple_value)
        except:
            # ingnore that silly data loss error....
            pass
        # x = np.array(range(len(adding_umc)))

        y = np.array(adding_umc)
        if window_size > 0:
            if len(y) < window_size:
                # raise ValueError('window size too large.')
                print('window_size too large')
            yhat = tensoboard_average(y, window_size)
        else:
            yhat = y
        xhat = np.linspace(0, y.shape[0], yhat.shape[0])
        xy_lst.append([[xhat, yhat], p])

    if filter_str:
        filtered_list = []
        for element in xy_lst:
            params_strs = element[-1].split('_')
            if filter_str in params_strs:
                filtered_list.append(element)
        return filtered_list
    else:
        return xy_lst
