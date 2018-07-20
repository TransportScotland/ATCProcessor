import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.dates as mdates
import pandas as pd

MONTH_LOCATOR = mdates.MonthLocator()
MONTH_FORMATTER = mdates.DateFormatter('%b\n%Y')


def yearly_scatter(data, datetime_col, value_col, category_col, colour_col,
                   dir_col, yearlong_x=True):
    # Get years without modifying existing frame
    year_values = data[datetime_col].dt.year

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
        # yield the figure so we can close the plot once it has been saved
        yield year, fig
        plt.close('all')
