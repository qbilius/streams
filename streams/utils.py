import functools

import numpy as np
import scipy.stats
import pandas
import matplotlib.pyplot as plt
import seaborn as sns


def splithalf(data, aggfunc=np.nanmean, rng=None):
    data = np.array(data)
    if rng is None:
        rng = np.random.RandomState(None)
    inds = list(range(data.shape[0]))
    rng.shuffle(inds)
    half = len(inds) // 2
    split1 = aggfunc(data[inds[:half]], axis=0)
    split2 = aggfunc(data[inds[half:2*half]], axis=0)
    return split1, split2


def pearsonr_matrix(data1, data2, axis=1):
    rs = []
    for i in range(data1.shape[axis]):
        d1 = np.take(data1, i, axis=axis)
        d2 = np.take(data2, i, axis=axis)
        r, p = scipy.stats.pearsonr(d1, d2)
        rs.append(r)
    return np.array(rs)


def spearman_brown_correct(pearsonr, n=2):
    pearsonr = np.array(pearsonr)
    return n * pearsonr / (1 + (n-1) * pearsonr)


def resample(data, rng=None):
    data = np.array(data)
    if rng is None:
        rng = np.random.RandomState(None)
    inds = rng.choice(range(data.shape[0]), size=data.shape[0], replace=True)
    return data[inds]


def bootstrap_resample(data, func=np.mean, niter=100, ci=95, rng=None):
    df = [func(resample(data, rng=rng)) for i in range(niter)]
    if ci is not None:
        return np.percentile(df, 50-ci/2.), np.percentile(df, 50+ci/2.)
    else:
        return df


def _timeplot_bootstrap(x, estimator=np.mean, ci=95, n_boot=100):
    ci = bootstrap_resample(x, func=estimator, ci=ci, niter=n_boot)
    return pandas.Series({'emin': ci[0], 'emax': ci[1]})


def timeplot(data=None, x=None, y=None, hue=None,
             estimator=np.mean, ci=95, n_boot=100,
             col=None, row=None, sharex=None, sharey=None,
             legend_loc='lower right', **fig_kwargs):
    if hue is None:
        hues = ['']
    else:
        hues = data[hue].unique()
        if data[hue].dtype.name == 'category': hues = hues.sort_values()

    # plt.figure()
    if row is None:
        row_orig = None
        tmp = 'row_{}'
        i = 0
        row = tmp.format(i)
        while row in data:
            i += 1
            row = tmp.format(i)
        data[row] = 'row'
    else:
        row_orig = row

    if col is None:
        col_orig = None
        tmp = 'col_{}'
        i = 0
        col = tmp.format(i)
        while col in data:
            i += 1
            col = tmp.format(i)
        data[col] = 'col'
    else:
        col_orig = col

    if row is not None:
        rows = data[row].unique()
        if data[row].dtype.name == 'category': rows = rows.sort_values()
    else:
        rows = [(None, None)]
    if col is not None:
        cols = data[col].unique()
        if data[col].dtype.name == 'category': cols = cols.sort_values()
    else:
        cols = [(None, None)]
    fig, axes = plt.subplots(nrows=len(rows), ncols=len(cols), **fig_kwargs)
    if hasattr(axes, 'shape'):
        axes = axes.reshape([len(rows), len(cols)])
    else:
        axes = np.array([[axes]])

    xlim = data.groupby([row, col])[x].apply(lambda x: {'amin': x.min(), 'amax': x.max()}).unstack()
    ylim = data.groupby([row, col])[y].apply(lambda x: {'amin': x.min(), 'amax': x.max()}).unstack()
    if sharex == 'row':
        for r in rows:
            xlim.loc[r, 'amin'] = xlim.loc[r, 'amin'].min()
            xlim.loc[r, 'amax'] = xlim.loc[r, 'amax'].max()
    elif sharex == 'col':
        for c in cols:
            xlim.loc[(slice(None), c), 'amin'] = xlim.loc[(slice(None), c), 'amin'].min()
            xlim.loc[(slice(None), c), 'amax'] = xlim.loc[(slice(None), c), 'amax'].max()
    elif sharex == 'both':
        xlim.loc[:, 'amin'] = xlim.loc[:, 'amin'].min()
        xlim.loc[:, 'amax'] = xlim.loc[:, 'amax'].min()
    elif isinstance(sharex, (tuple, list)):
        xlim.loc[:, 'amin'] = sharex[0]
        xlim.loc[:, 'amax'] = sharex[1]

    if sharey == 'row':
        for r in rows:
            ylim.loc[r, 'amin'] = ylim.loc[r, 'amin'].min()
            ylim.loc[r, 'amax'] = ylim.loc[r, 'amax'].max()
    elif sharey == 'col':
        for c in cols:
            ylim.loc[(slice(None), c), 'amin'] = ylim.loc[(slice(None), c), 'amin'].min()
            ylim.loc[(slice(None), c), 'amax'] = ylim.loc[(slice(None), c), 'amax'].max()
    elif sharey == 'both':
        ylim.loc[:, 'amin'] = ylim.loc[:, 'amin'].min()
        ylim.loc[:, 'amax'] = ylim.loc[:, 'amax'].min()
    elif isinstance(sharey, (tuple, list)):
        ylim.loc[:, 'amin'] = sharey[0]
        ylim.loc[:, 'amax'] = sharey[1]

    for rno, r in enumerate(rows):
        for cno, c in enumerate(cols):
            ax = axes[rno,cno]
            for h, color in zip(hues, sns.color_palette(n_colors=len(hues))):
                if hue is None:
                    d = data
                else:
                    d = data[data[hue] == h]

                sel_col = d[col] == c if col is not None else True
                sel_row = d[row] == r if row is not None else True
                if not (col is None and row is None):
                    d = d[sel_row & sel_col]

                # if c == 'hvm_test': import ipdb; ipdb.set_trace()
                if len(d) > 0:
                    mn = d.groupby(x)[y].apply(estimator)
                    def bootstrap(x):
                        try:
                            y = _timeplot_bootstrap(x[x.notnull()], estimator, ci, n_boot)
                        except:
                            y = _timeplot_bootstrap(x, estimator, ci, n_boot)
                        return y

                    if n_boot > 0:
                        ebars = d.groupby(x)[y].apply(bootstrap).unstack()
                        ax.fill_between(mn.index, ebars.emin, ebars.emax, alpha=.5, color=color)

                    ax.plot(mn.index, mn, linewidth=2, color=color, label=h)
                else:
                    ax.set_visible(False)

            try:
                ax.set_xlim([xlim.loc[(r, c), 'amin'], xlim.loc[(r, c), 'amax']])
            except:
                pass
            try:
                ax.set_ylim([ylim.loc[(r, c), 'amin'], ylim.loc[(r, c), 'amax']])
            except:
                pass

            if ax.is_last_row():
                ax.set_xlabel(x)
            if ax.is_first_col():
                ax.set_ylabel(y)

            if row_orig is None:
                if col_orig is None:
                    ax.set_title('')
                else:
                    ax.set_title('{} = {}'.format(col_orig, c))
            else:
                if col_orig is None:
                    ax.set_title('{} = {}'.format(row_orig, r))
                else:
                    ax.set_title('{} = {} | {} = {}'.format(row_orig, r, col_orig, c))

            if hue is not None:
                plt.legend(loc=legend_loc, framealpha=.25)

    plt.tight_layout()
    return axes


def clean_data(df, std_thres=3, stim_dur_thres=1000./120):
    """
    Remove outliers from behavioral data

    What is removed:
        - If response time is more than `std_thres` standard deviations above
          the mean response time to all stimuli (default: 3)
        - If the recorded stimulus duration differs by more than `std_thres`
          from the requested stimulus duration (default: half a frame for 60 Hz)

    :Args:
        df - pandas.DataFrame

    :Kwargs:
        - std_thres (float, default: 3)
        - stim_dur_thres (float, default: 1000./120)

    :Returns:
        pandas.DataFrame that has the outliers removed (not nanned)
    """
    fast_rts = np.abs(df.rt - df.rt.mean()) < 3 * df.rt.std()
    good_present_time = np.abs(df.actual_stim_dur - df.stim_dur) < stim_dur_thres  # half a frame
    print('Response too slow: {} out of {}'.format(len(df) - fast_rts.sum(), len(df)))
    print('Stimulus presentation too slow: {} out of {}'.format(len(df) - good_present_time.sum(), len(df)))
    df = df[fast_rts & good_present_time]
    return df


def lazy_property(function):
    """
    From: https://danijar.com/structuring-your-tensorflow-models/
    """
    attribute = '_cache_' + function.__name__

    @property
    @functools.wraps(function)
    def decorator(self):
        if not hasattr(self, attribute):
            setattr(self, attribute, function(self))
        return getattr(self, attribute)

    return decorator


# def hitrate_to_dprime(df, cap=5):
#     # df = pandas.DataFrame(hitrate, index=labels, columns=order)
#     out = np.zeros_like(df)
#     for (i,j), hit_rate in np.ndenumerate(df.values):
#         target = df.index[i]
#         distr = df.columns[j]
#         if target == distr:
#             dprime = np.nan
#         else:
#             miss_rate = df.loc[df.index == target, distr].mean()
#             hit = hit_rate / (hit_rate + miss_rate)
#             fa_rate = df.loc[df.index == distr, target].mean()
#             rej_rate = df.loc[df.index == distr, distr].mean()
#             fa = fa_rate / (fa_rate + rej_rate)
#             dprime = scipy.stats.norm.ppf(hit) - scipy.stats.norm.ppf(fa)
#             if dprime > cap: dprime = cap
#         out[i,j] = dprime

#     return out


def hitrate_to_dprime_o1(df, cap=20):
    # df = pandas.DataFrame(hitrate, index=labels, columns=order)
    targets = df.index.unique()
    # distrs = df.columns.unique()
    # out = pandas.DataFrame(np.zeros([len(targets), len(distrs)]), index=targets, columns=distrs)
    out = pandas.Series(np.zeros(len(targets)), index=targets)
    for target in targets:
        # if target == 'lo_poly_animal_RHINO_2': import ipdb; ipdb.set_trace()
        hit_rate = np.nanmean(df.loc[df.index == target])
        # miss_rate = 1 - np.nanmean(df.loc[df.index == target])
        fa_rate = np.nanmean(1 - df.loc[df.index != target, target])
        dprime = scipy.stats.norm.ppf(hit_rate) - scipy.stats.norm.ppf(fa_rate)
        dprime = np.clip(dprime, -cap, cap)
        out[target] = dprime
    return out
    #     for distr in distrs:
    # # for (i,j), hit_rate in np.ndenumerate(df.values):
    #         if target == distr:
    #             dprime = np.nan
    #         else:
    #             hit_rate = df.loc[df.index == target].mean()
    #             miss_rate = df.loc[df.index == target, distr].mean()
    #             hit = hit_rate / (hit_rate + miss_rate)
    #             fa_rate = df.loc[df.index == distr, target].mean()
    #             rej_rate = df.loc[df.index == distr, distr].mean()
    #             fa = fa_rate / (fa_rate + rej_rate)
    #             dprime = scipy.stats.norm.ppf(hit) - scipy.stats.norm.ppf(fa)
    #             if dprime > cap: dprime = cap
    #         out[target, distr] = dprime

    # return out





def hitrate_to_dprime_i1n(df, cap=20, normalize=True):
    out = pandas.Series(np.zeros(len(df)),
                        index=df.set_index(['obj', 'id']).index)
    for (target, idd), row in df.iterrows():
        hit_rate = row.acc
        # miss_rate = 1 - np.nanmean(df.loc[df.index == target])
        rej = df.loc[df.obj != target, target]
        fa_rate = 1 - np.nanmean(rej)
        dprime = scipy.stats.norm.ppf(hit_rate) - scipy.stats.norm.ppf(fa_rate)
        dprime = np.clip(dprime, -cap, cap)
        out.loc[(target, idd)] = dprime

    if normalize:
        out.acc -= out.groupby('obj').acc.transform(lambda x: x.mean())
    return out


def hitrate_to_dprime_i2n(df, cap=20):
    # df = pandas.DataFrame(hitrate, index=labels, columns=order)
    # targets = df.index.unique()
    # distrs = df.columns.unique()
    # out = pandas.DataFrame(np.zeros([len(targets), len(distrs)]), index=targets, columns=distrs)
    # df = df.set_index(['obj', 'id', 'distr'])
    # out = pandas.DataFrame(np.zeros(len(df), len(df.distr.unique()), index=df.index, columns=df.columns)
    out = df.set_index(['obj', 'id', 'distr']).copy()
    for (target, idd, distr), hit_rate in out.iterrows():

        if target == distr:
            out.loc[(target, idd, distr)] = np.nan
        else:
            # if target == 'lo_poly_animal_RHINO_2': import ipdb; ipdb.set_trace()
            # hit_rate = acc
            # miss_rate = 1 - np.nanmean(df.loc[df.index == target])
            rej = df.loc[(df.obj == distr) & (df.distr == target), 'acc']
            # import ipdb; ipdb.set_trace()
            fa_rate = 1 - np.nanmean(rej)
            dprime = scipy.stats.norm.ppf(hit_rate) - scipy.stats.norm.ppf(fa_rate)

            # if target == 'lo_poly_animal_RHINO_2' and distr == 'MB30758' and idd == 'e387f6375d1d01a92f02394ea0c2c89de4ec4f61':
            #     import ipdb; ipdb.set_trace()

            # hit_rate_norm = np.nanmean(df.loc[(df.obj == target) & (df.distr == distr), 'acc'])
            # dprime_norm = scipy.stats.norm.ppf(hit_rate_norm) - scipy.stats.norm.ppf(fa_rate)

            # dprime -= dprime_norm

            out.loc[(target, idd, distr)] = dprime

    # def ff(x):
    #     import ipdb; ipdb.set_trace()
    #     return x.mean()

    out = out.reset_index()
    out.acc -= out.groupby(['obj', 'distr']).acc.transform(lambda x: x.mean())
    out.acc = np.clip(out.acc, -cap, cap)

    # for (target, idd, distr), dprime in out.iterrows():

    #     out.loc[(target, idd, distr)] = dprime

    # dprime = np.clip(dprime, -cap, cap)
    return out