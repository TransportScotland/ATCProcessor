import os

from matplotlib import use
use('TKAgg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns

from .utilities import make_folder_if_necessary
from .version import VERSION_TITLE
from .calmap import calmap

sns.set(style='whitegrid')

VERSION_TEXT = '''
Produced by {}
'''.format(VERSION_TITLE)

MONTH_LOCATOR = mdates.MonthLocator()
MONTH_FORMATTER = mdates.DateFormatter('%b\n%Y')


def yearly_scatter(data, datetime_col, value_col, category_col, colour_col,
                   dir_col, destination_path, yearlong_x=True):
    # Get years without modifying existing frame
    year_values = data[datetime_col].dt.year

    make_folder_if_necessary(destination_path)

    # Group by year, set up a plot per year
    for year, year_data in data.groupby(year_values):
        # Create a subplot per direction
        directions = len(year_data[dir_col].unique())
        fig, axes = plt.subplots(nrows=directions, sharex=True, sharey=True,
                                 figsize=(14, 4*directions + 1))

        # When only one direction present, doesn't return a list.
        # Put into a list for ease of following processing
        if directions == 1:
            axes = [axes]

        # Group by direction
        for i, (direction, dir_data) in enumerate(year_data.groupby(dir_col)):
            axes[i].set_title(direction)
            # Plot all statuses with the right colour
            for status, status_data in dir_data.groupby(category_col):
                plot_data = status_data.set_index(datetime_col)
                axes[i].scatter(plot_data.index, plot_data[value_col],
                                c=plot_data[colour_col],
                                s=0.6, label=status)

            axes[i].set_ylabel('Flow (vehs/hour)')

        # Make axes prettier
        axes[0].margins(x=0)
        axes[0].set_ylim(bottom=0)
        axes[0].xaxis.set_major_locator(MONTH_LOCATOR)
        axes[0].xaxis.set_major_formatter(MONTH_FORMATTER)

        # If we want to show the entire year, do so!
        if yearlong_x:
            axes[0].set_xlim(left=pd.to_datetime('{}/01/01'.format(year)),
                             right=pd.to_datetime('{}/01/01'.format(year+1))
                                   - pd.to_timedelta(1, unit='s'))

        # Use patches for larger colours on legend, consistency across
        # directions.
        colour_patches = [Patch(color=c, label=s)
                          for (c, s), _
                          in year_data.groupby([colour_col, category_col])]

        axes[-1].legend(handles=colour_patches, ncol=5, loc='upper center',
                        bbox_to_anchor=(0.5, -0.15), fancybox=True)
        plt.tight_layout()
        dest = '_{}'.format(year).join(os.path.splitext(destination_path))
        plt.savefig(dest, bbox_to_inches='tight')
        plt.close('all')


def calendar_plot(data, count_column, destination_path, maxval=None):
    if maxval is None:
        maxval = data[count_column].max()

    fig, ax = calmap.calendarplot(
        data[count_column], cmap='RdYlBu',
        yearlabel_kws=dict(color='k', size='large'),
        how=None, monthseparator=True, separatorwidth=1,
        vmax=maxval, #fillcolor='white',
        fig_kws=dict(figsize=(8, 8))
    )

    # Add colour bar and watermark.
    cbar = fig.colorbar(ax[0].get_children()[1], ax=ax.ravel().tolist(),
                        pad=0.1)
    cbar.outline.set_edgecolor('black')
    cbar.ax.set_ylabel('Total traffic (vehs)')

    cbar.ax.text(-0.2, 0.5, VERSION_TEXT,
                 rotation=90, alpha=0.5,
                 va='center', ha='center',
                 size='x-small')

    make_folder_if_necessary(destination_path)
    plt.savefig(destination_path, bbox_to_inches='tight')
    plt.close('all')


def atc_facet_grid(data, separate_rows, x, y, destination_path,
                   separate_cols=None, hue=None):
    g = sns.FacetGrid(data, row=separate_rows, col=separate_cols,
                      # hue=hue, height=1.5, aspect=4,
                      hue=hue, height=1.4, aspect=2.7,
                      legend_out=True, margin_titles=True)
    g.map(plt.plot, x, y, marker=None)
    g.add_legend()
    g.axes[-1, 0].set_xlabel(x)

    g.axes[0, 0].margins(x=0)

    if x.lower() == 'hour':
        g.set(xticks=range(0, 24, 2))
        g.set_xticklabels(['{:02d}:00'.format(x) for x in range(0, 24, 2)],
                          rotation=90)
        # Rotating the labels cuts off the "Hour" label.
        # plt.tight_layout() moves the legend, so add some spacing instead
        plt.subplots_adjust(bottom=0.08)
    g.axes[0, 0].set_ylim(bottom=0)

    # Clear original text before adding titles
    for ax in g.axes.flat:
        plt.setp(ax.texts, text="")

    g.set_titles(row_template='{row_name}', col_template='{col_name}')
    make_folder_if_necessary(destination_path)
    plt.savefig(destination_path, bbox_to_inches='tight')
    plt.close('all')
