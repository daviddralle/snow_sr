# importing
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Set plotting parameters
plt.rcParams.update({'font.size': 20})
plt.rcParams['font.family'] = "serif"
plt.rcParams['font.serif'] = "Times New Roman"
plt.rcParams['axes.grid'] = False
plt.rcParams['axes.axisbelow'] = True
plt.rcParams['axes.labelpad'] = 6


def main():

    data, merged_interpolated_data = import_data()

    data_w_calcs = deficit_calcs(data=merged_interpolated_data, snow_frac=10)

    multi_site_plotting_fig(data=data_w_calcs, file_name='figs/comparison_fig_20201106_2row.png',
                            titles=['High Snow Location', 'Low Snow Location'],
                            points_plotting=[0, 1], start_year=2013, end_year=2017)


def import_data():
    clim = pd.read_csv("data/clim_gee_export.csv")
    clim.drop(columns=["Unnamed: 0"], inplace=True)
    modis = pd.read_csv("data/modis_gee_export.csv")
    modis.drop(columns=["Unnamed: 0"], inplace=True)
    data = pd.merge(clim, modis, how='left', on=['id', 'point'])
    data['id'] = pd.to_datetime(data['id'])
    data['modis_ET'] = data['modis_ET']/8
    data['modis_PET'] = data['modis_PET']/8

    # All data columns to keep
    merged_interpolated_data = data[['id', 'point', 'prism_ppt', 'prism_tdmean', 'prism_tmax', 'prism_tmean',
                                    'prism_tmin', 'prism_vpdmax', 'prism_vpdmin', 'pml_Ec', 'pml_Ei', 'pml_Es',
                                    'pml_GPP', 'pml_qc', 'snow_cover_modis_NDSI', 'snow_cover_modis_NDSI_Snow_Cover',
                                    'modis_ET', 'modis_LE', 'modis_PET', 'modis_PLE', 'modis_DayOfYear', 'modis_EVI',
                                     'modis_NDVI']]

    # Interpolating for all dates
    for i in merged_interpolated_data['point'].unique():
        temp = merged_interpolated_data[merged_interpolated_data['point'] == i]
        temp = temp.interpolate(method='linear', limit_direction='both')
        merged_interpolated_data.loc[merged_interpolated_data['point'] == i] = temp

    return data, merged_interpolated_data


def deficit_calcs(data, snow_frac):
    print(data.columns)
    data['ET'] = data['pml_Ec']+data['pml_Es']
    data['No Snow ET'] = data['ET']
    data.loc[data['snow_cover_modis_NDSI_Snow_Cover'] > snow_frac, 'No Snow ET'] = 0
    data['A_old'] = data['ET'] - data['prism_ppt']
    data['A_new'] = data['No Snow ET'] - data['prism_ppt']

    data['D_old'] = 0
    data['D_new'] = 0

    new_data = pd.DataFrame()
    for i in data['point'].unique():
        mid0 = data.loc[data['point'] == i]
        mid0 = mid0.reset_index(drop=True)
        mid0['A_cumulative_new'] = mid0['A_new'].cumsum()
        mid0['A_cumulative_old'] = mid0['A_old'].cumsum()

        for _i in range(mid0.shape[0]-1):
            mid0.loc[_i+1, 'D_old'] = max((mid0.loc[_i+1, 'A_old'] + mid0.loc[_i, 'D_old']), 0)
            mid0.loc[_i+1, 'D_new'] = max((mid0.loc[_i+1, 'A_new'] + mid0.loc[_i, 'D_new']), 0)

        new_data = new_data.append(mid0)

    return new_data

# plotting
def multi_site_plotting_fig(data, file_name, points_plotting, titles, start_year, end_year):

    # setting line widths for plots
    lw_old = 3
    lw_new = 3

    # setting y limits for different plots
    et_range = [-0.25, 4.75]
    d_range = [-50, 1200]

    # Setting starting point of axes on the plots, this is for two sites
    sides = [0.0, 0.5]
    row_fracs = [0.0, 0.5]

    width_frac = 0.85/len(points_plotting)
    height_frac = 0.45

    # Dealing with date tick marks
    # format the ticks

    data = data[(data['id'].dt.year >= start_year) & (data['id'].dt.year <= end_year)]

    fig = plt.figure(figsize=(12, 6))

    for i in range(len(points_plotting)):
        # selecting data for selected point
        plot_data = data.loc[data['point'] == points_plotting[i]]
        #
        # # adding precip plot
        ax = fig.add_axes([sides[i], row_fracs[0], width_frac, height_frac])
        ylims = et_range
        a = 1
        ax.plot(plot_data['id'], plot_data['ET'], linewidth=lw_old, color='dimgray',label='Original Method', zorder=1, alpha=a)
        ax.plot(plot_data['id'], plot_data['No Snow ET'], linewidth=1, color='black', label='Snow-accounting Method', zorder=4, alpha=a)
        ax.vlines(plot_data.loc[plot_data['No Snow ET'] == 0]['id'], ylims[0], ylims[1],
                  alpha=0.35, lw=0.1, colors='gray', zorder=0)

        ax.set_ylim(ylims)
        if i == 0:
            ax.set_ylabel('Evapotranspiration \n'+r'(F$_{in}$'+', mm/day)\n   ')
        # format the coords message box
        ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
        locs, labels = plt.xticks()
        locs = [loc for _loc, loc in enumerate(locs) if _loc % 2 == 0]
        plt.xticks(locs, rotation=40)

        # adding deficit axis
        ax = fig.add_axes([sides[i], row_fracs[1], width_frac, height_frac], xticklabels=[])
        ylims = d_range
        ax.plot(plot_data['id'], plot_data['D_old'], linewidth=lw_old, color='dimgray', label='Original Method')
        ax.plot(plot_data['id'], plot_data['D_new'], linewidth=1, color='black', label='Snow-accounting Method')
        ax.vlines(plot_data.loc[plot_data['No Snow ET'] == 0]['id'], ylims[0], ylims[1],
                  alpha=0.5, lw=0.1, colors='gray', zorder=1)
        ax.set_ylim(ylims)

        if i == 0:
            ax.set_ylabel('Root zone storage deficit \n (D, mm)')
            ax.legend(loc='upper left', prop={'size': 12})
        ax.set_title(titles[i])

    plt.savefig(file_name, bbox_inches='tight')

if __name__ == "__main__":
    main()
