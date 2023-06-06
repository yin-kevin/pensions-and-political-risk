#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 26 21:13:29 2023

@author: kevinyin
"""


#%% imports

import os
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors


# 1. root directory
directory_path = os.path.realpath(__file__)[:-21]
os.chdir(directory_path)

# 2. data path
data_path = os.path.join(directory_path, "data")

# 3. Image output path
output_path = os.path.join(directory_path, "figures")





#%% data

# IMF investment data
dict_imf_jun = {}
dict_imf_dec = {}

for y in range(2013,2023):
        key = y
        dict_imf_jun[key] = pd.read_excel(os.path.join(data_path, "imf", f"allinvest_june{y}.xlsx"))
        if y < 2022:
            dict_imf_dec[key] = pd.read_excel(os.path.join(data_path, "imf", f"allinvest_dec{y}.xlsx"))
    
    
# geopolitical risk data
df_gpr = pd.read_excel(os.path.join(data_path, "gpr", "geo_risk_index.xls"))


# OECD total asset data
df_pension_assets = pd.read_csv(os.path.join(data_path, "oecd", "total_pension_assets.csv"))
df_pension_gdp = pd.read_csv(os.path.join(data_path, "oecd", "total_pension_assets_perc.csv"))

# FIXME: the data you downloaded doesnt work from 2018 to 2021
# OECD asset structure
dict_oecd = {}

for y in range(2006,2022):
    key = y
    dict_oecd[key] = pd.read_excel(os.path.join(data_path, "oecd", f"pension_asset_struct{y}.xlsx"))


# exchange rates
df_exrate_raw = pd.read_csv(os.path.join(data_path, "exchange_rates_oecd.csv"))





#%% functions & settings


# cleans imf dataframes
def clean_imf(df):

    # remove empty columns and rows (or those with commentary)
    df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1'])
    df = df.iloc[3:]
    df.columns = df.iloc[0]
    df.reset_index(inplace=True)
    df = df.iloc[1:247]
    df = df.drop(columns=['index','SEFER + SSIO (**)'])
    
    # save names of destination countries
    destination = df[['Investment in:']]
    destination = destination.rename(columns={'Investment in:':'destination'})
    df = df.drop(columns='Investment in:').apply(pd.to_numeric, errors='coerce')
    df = pd.concat([destination, df], axis=1)

    # return cleaned data
    return df



# get time series of investments and share of total foreign investment from source to dest.
def timeseries_imf(source, destination):
    
    yrs_list = []
    mth_list = []
    inv_list = []
    tot_list = []
    
    # extract investment flows from source to destination for each year
    for i in range(2013,2023):
        
        # add year to list
        yrs_list.append(i)
        mth_list.append(6)
        
        # choose dataframe
        df = clean_imf(dict_imf_jun[i])
        
        # find investment from source to destination
        countries = df[['destination']]
        ctry_index = countries.index[countries['destination'] == destination]
        inv = df.loc[ctry_index[0], source]
        inv_list.append(inv)
        
        # find total investment and calculate percentage of total
        wrld_index = countries.index[countries['destination'] == 'World']
        tot = df.loc[wrld_index[0], source]
        tot_list.append(tot)
        
        # clean december data
        if i < 2022:
            
            # add year to list
            yrs_list.append(i)
            mth_list.append(12)
            
            # choose dataframe
            df = clean_imf(dict_imf_dec[i])
            
            # find investment from source to destination
            countries = df[['destination']]
            ctry_index = countries.index[countries['destination'] == destination]
            inv = df.loc[ctry_index[0], source]
            inv_list.append(inv)
            
            # find total investment and calculate percentage of total
            wrld_index = countries.index[countries['destination'] == 'World']
            tot = df.loc[wrld_index[0], source]
            tot_list.append(tot)
    
    # create dataframe out of years and investments
    df_output = pd.DataFrame({'year': yrs_list, 'month': mth_list, 'inv_in_dest': inv_list, 'total_inv': tot_list})
    df_output['inv_share'] = df_output['inv_in_dest'] / df_output['total_inv']
    return df_output



# cleans oecd asset-class dataframes
def clean_oecd(df):
    
    # retrieve columns
    col1 = df.iloc[7:8]
    col2 = df.iloc[8:9]
    
    # move mutual fund assets into columns
    col1['Unnamed: 8'] = col2.loc[8]['Unnamed: 8']
    col1['Unnamed: 9'] = col2.loc[8]['Unnamed: 9']
    col1['Unnamed: 10'] = col2.loc[8]['Unnamed: 10']
    col1['Unnamed: 11'] = col2.loc[8]['Unnamed: 11']
    col1['Unnamed: 12'] = col2.loc[8]['Unnamed: 12']
    
    # clean up
    df = df.iloc[9:]
    df = pd.concat([col1, df], axis=0)
    df.columns = df.loc[7]
    df = df.iloc[2:]
    df = df.drop(columns=np.nan)
    
    # rename
    df = df.rename(columns={'Variable':'country',
                                  'Cash and Deposits':'cash',
                                  'Bills and bonds issued by public and private sector':'bonds',
                                  'Loans':'loans',
                                  'Equity':'equity',
                                  'Mutual funds (CIS)':'mutual funds',
                                  'Land and Buildings':'real estate',
                                  'Hedge funds':'hedge funds',
                                  'Private equity funds':'private equity',
                                  'Other investments': 'other'})
    
    # turn to numeric
    countries = df['country']
    df = df.apply(pd.to_numeric, errors='coerce').drop(columns='country')
    
    # if a row has any entry, fill the nans with 0s
    for i in range(0, len(df)):
        if df.iloc[i].isnull().all() == False:
            df.iloc[i] = df.iloc[i].fillna(0)
    
    # re-attach countries
    df = pd.concat([countries,df], axis=1)
    
    
    # collapse mutual fund holdings into other categories 
    # NOTE: deposits are cash, loans and bills are bonds, structured products and unallocated insurance are other
    df['cash'] = df['cash'] + ((df['mutual funds'] / 100) * df['Of which: Cash and deposits'])
    df['bonds'] = df['bonds'] + df['loans'] + ((df['mutual funds'] / 100) * df['Of which: Bills and bonds']) 
    df['equity'] = df['equity'] + ((df['mutual funds'] / 100) * df['Of which: Equity'])
    df['real estate'] = df['real estate'] + ((df['mutual funds'] / 100) * df['Of which: Land and buildings'])
    df['other'] = df['other'] + ((df['mutual funds'] / 100) * df['Of which: Other']) + df['Structured products'] + df['Unallocated insurance contracts']
    
    
    # drop mutual fund holdings and sum to check
    mutual_funds = df['mutual funds']
    df = df[['country','cash','bonds','equity','real estate','other']]
    df['sum']=df.sum(axis=1)
    
    # for those countries with unknown mutual fund holds of >10% (usually like 20-30%, use known allocation ratio
    df['mtf_unknown'] = df['sum'] < 90
    df['mutual funds'] = mutual_funds
    
    # compute allocation ratios
    df['mtf_cash_share'] = 100 * df['cash'] / (100 - df['mutual funds'])
    df['mtf_bond_share'] = 100 * df['bonds'] / (100 - df['mutual funds'])
    df['mtf_equity_share'] = 100 * df['equity'] / (100 - df['mutual funds'])
    df['mtf_realest_share'] = 100 * df['real estate'] / (100 - df['mutual funds'])
    df['mtf_other_share'] = 100 * df['other'] / (100 - df['mutual funds'])
    
    # if the mutual fund subcategory holdings were missing, replace our current data with known rates
    df.loc[df.mtf_unknown == True, 'cash'] = df.loc[df.mtf_unknown == True, 'mtf_cash_share']
    df.loc[df.mtf_unknown == True, 'bonds'] = df.loc[df.mtf_unknown == True, 'mtf_bond_share']
    df.loc[df.mtf_unknown == True, 'equity'] = df.loc[df.mtf_unknown == True, 'mtf_equity_share']
    df.loc[df.mtf_unknown == True, 'real estate'] = df.loc[df.mtf_unknown == True, 'mtf_realest_share']
    df.loc[df.mtf_unknown == True, 'other'] = df.loc[df.mtf_unknown == True, 'mtf_other_share']
    
    # drop all the extra columns
    df = df[['country','cash','bonds','equity','real estate','other','mtf_unknown']]
    df = df[:-1]

    return df


def timeseries_assetclass(country, asset):
    
    # initialize
    years_list = []
    asset_list = []
    
    for i in range(2006,2022):
        
         # add year to list
        years_list.append(i)
        
        # add bond value to list
        df = clean_oecd(dict_oecd[i])
        asset_value = df.loc[df['country'] == country, asset].item()
        
        # add asset value to list
        asset_list.append(asset_value)

    # create dataframe out of years and asset allocations
    df_output = pd.DataFrame({'year': years_list, country: asset_list})
    return df_output



# set lists of countries to use later
g7_list = ['United States', 'United Kingdom', 'Japan', 'Germany', 'France', 'Italy', 'Canada']
oecd_aclass_list = ['Canada', 'United States', 'United Kingdom', 'Germany', 'Australia', 'Italy', 'Netherlands', 'Norway']





#%% create investment time series


# initialize
df_inv_in_china = timeseries_imf('United States', 'China, P.R.: Mainland')
df_inv_in_china = df_inv_in_china[['year','month']]

df_share_in_china = timeseries_imf('United States', 'China, P.R.: Mainland')
df_share_in_china = df_share_in_china[['year','month']]

df_totalinv = timeseries_imf('United States', 'China, P.R.: Mainland')
df_totalinv = df_totalinv[['year','month']]


# loop through G7 countries
for country in g7_list:
    df_temp = timeseries_imf(country, 'China, P.R.: Mainland')
    df_temp = df_temp.rename(columns={'inv_in_dest':f'{country}'})
    df_inv_in_china = pd.concat([df_inv_in_china, df_temp[[f'{country}']]], axis=1)

    
    df_temp = timeseries_imf(country, 'China, P.R.: Mainland')
    df_temp = df_temp.rename(columns={'inv_share':f'{country}'})
    df_share_in_china = pd.concat([df_share_in_china, df_temp[[f'{country}']]], axis=1)
    
    df_temp = timeseries_imf(country, 'China, P.R.: Mainland')
    df_temp = df_temp.rename(columns={'total_inv':f'{country}'})
    df_totalinv = pd.concat([df_totalinv, df_temp[[f'{country}']]], axis=1)


# set time to index for plotting
df_inv_in_china = df_inv_in_china.set_index(['year','month'])
df_share_in_china = df_share_in_china.set_index(['year','month'])
df_totalinv = df_totalinv.set_index(['year','month'])


# set to the appropriate units
df_totalinv = df_totalinv / 1000000 # trillions
df_share_in_china = df_share_in_china * 100 # percentage
df_inv_in_china = df_inv_in_china / 1000 # billions





#%% clean total pension data

# clean exchange rates
df_exrate = df_exrate_raw[['LOCATION','TIME','Value']]
df_exrate['LOCATION'] = df_exrate['LOCATION'].str.replace('DEU','EUR')
df_exrate = df_exrate.rename(columns={'LOCATION':'currency','TIME':'year','Value':'unit_per_usd'})

# clean pension data
df_total_pension = df_pension_assets[['Variable','Country','Year','Unit','Unit Code','Value']]
df_total_pension = df_total_pension[df_total_pension['Variable'] == 'INVESTMENT']
df_total_pension = df_total_pension.rename(columns={'Country':'ctry_name',
                                                    'Year':'year',
                                                    'Unit Code':'currency',
                                                    'Value':'totassets'})

# replace currencies with country names
df_total_pension['currency'] = df_total_pension['currency'].str.replace('AUD','AUS')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('USD','USA')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('CAD','CAN')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('DKK','DNK')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('CZK','CZE')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('JPY','JPN')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('KRW','KOR')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('MXN','MEX')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('NZD','NZL')

df_total_pension['currency'] = df_total_pension['currency'].str.replace('HUF','HUN')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('ISK','ISL')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('PLN','POL')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('SEK','SWE')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('CHF','CHE')

df_total_pension['currency'] = df_total_pension['currency'].str.replace('TRY','TUR')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('GBP','GBR')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('CLP','CHL')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('COP','COL')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('CRC','CRI')
df_total_pension['currency'] = df_total_pension['currency'].str.replace('ILS','ISR')

# merge
df_total_pension = df_total_pension.merge(df_exrate, how='left', on=['currency','year'])

# calculate assets in USD
df_total_pension['totassets_usd'] = df_total_pension['totassets'] / df_total_pension['unit_per_usd']


# clean and reshape for plotting
df_total_pension = df_total_pension[['ctry_name','year','totassets_usd']]
df_temp = df_total_pension['year'].sort_values().unique()
df_total_pension = df_total_pension.pivot_table(index=['year'], columns='ctry_name',  values='totassets_usd')





#%% clean pension % data

# convert to numeric
pension_countries = df_pension_gdp['country']
df_pens_gdp_clean = df_pension_gdp.drop(columns='country')
df_pens_gdp_clean = df_pens_gdp_clean.apply(pd.to_numeric, errors='coerce')
df_pens_gdp_clean = pd.concat([pension_countries,df_pens_gdp_clean], axis=1)

# keep only G7
df_pens_gdp_clean = df_pens_gdp_clean[df_pens_gdp_clean['country'].isin(g7_list)]
df_pens_gdp_clean = df_pens_gdp_clean.transpose()
df_pens_gdp_clean.columns = df_pens_gdp_clean.iloc[0]
df_pens_gdp_clean = df_pens_gdp_clean.drop(df_pens_gdp_clean.index[0])
df_pens_gdp_clean = df_pens_gdp_clean.apply(pd.to_numeric, errors='coerce')

# drop Japan since data is bad
df_pens_gdp_clean = df_pens_gdp_clean.drop(columns='Japan')

# keep only last 2 decades
df_pens_gdp_clean.index = pd.to_numeric(df_pens_gdp_clean.index, downcast='integer', errors='coerce')
df_pens_gdp_clean = df_pens_gdp_clean[df_pens_gdp_clean.index > 2001]
df_pens_gdp_clean.index = df_pens_gdp_clean.index.map(str)





#%% clean oecd asset class

# prepare most recent asset class data
df_g7_assets_2021 = clean_oecd(dict_oecd[2021])
df_g7_assets_2021 = df_g7_assets_2021[df_g7_assets_2021['country'].isin(oecd_aclass_list)]
df_g7_assets_2021['sum'] = df_g7_assets_2021.sum(axis=1)
df_g7_assets_2021.loc[df_g7_assets_2021['country'] == 'United States', 'sum'] = 100.00132 # hard code US sum for some reason
df_g7_assets_2021['multiplier'] = 100 / df_g7_assets_2021['sum']

df_g7_assets_2021['cash'] = df_g7_assets_2021['cash'] * df_g7_assets_2021['multiplier']
df_g7_assets_2021['bonds'] = df_g7_assets_2021['bonds'] * df_g7_assets_2021['multiplier']
df_g7_assets_2021['equity'] = df_g7_assets_2021['equity'] * df_g7_assets_2021['multiplier']
df_g7_assets_2021['real estate'] = df_g7_assets_2021['real estate'] * df_g7_assets_2021['multiplier']
df_g7_assets_2021['other'] = df_g7_assets_2021['other'] * df_g7_assets_2021['multiplier']
df_g7_assets_2021['country'] = df_g7_assets_2021['country'].str.replace('United States', '*United States')


# clean
df_g7_assets_2021 = df_g7_assets_2021.drop(columns=['sum','multiplier'])
df_g7_assets_2021 = df_g7_assets_2021[['country','bonds','equity','real estate','cash','other']]
df_g7_assets_2021 = df_g7_assets_2021.sort_values(by = 'bonds', axis = 0)


# prepare time series of cash holdings
df_init = timeseries_assetclass('Canada', 'cash')
df_init = df_init.drop(columns='Canada')
df_list = [df_init]

for country in oecd_aclass_list:
    df = timeseries_assetclass(country, 'cash')
    df = df.drop(columns='year')
    df_list.append(df)
    
df_cash_holdings = pd.concat(df_list, axis=1)
df_cash_holdings = df_cash_holdings.set_index('year')


# prepare time series of bond holdings
df_init = timeseries_assetclass('Canada', 'bonds')
df_init = df_init.drop(columns='Canada')
df_list = [df_init]

for country in oecd_aclass_list:
    df = timeseries_assetclass(country, 'bonds')
    df = df.drop(columns='year')
    df_list.append(df)
    
df_bond_holdings = pd.concat(df_list, axis=1)
df_bond_holdings = df_bond_holdings.set_index('year')


# prepare time series of equity holdings
df_init = timeseries_assetclass('Canada', 'equity')
df_init = df_init.drop(columns='Canada')
df_list = [df_init]

for country in oecd_aclass_list:
    df = timeseries_assetclass(country, 'equity')
    df = df.drop(columns='year')
    df_list.append(df)
    
df_equity_holdings = pd.concat(df_list, axis=1)
df_equity_holdings = df_equity_holdings.set_index('year')





#%% clean GPR

# cut NaNs, start from 2000
df_gpr_plot = df_gpr
df_gpr_plot = df_gpr_plot.set_index('month')
df_gpr_plot = df_gpr_plot[~df_gpr_plot['GPRC_CHN'].isna()]
df_gpr_plot = df_gpr_plot[df_gpr_plot.index >= pd.Timestamp('1999-02-01')]

# restrict to countries of interest
df_gpr_plot = df_gpr_plot[['GPR','GPRC_CHN','GPRC_TWN','GPRC_HKG']]

# compute moving averages
df_gpr_mavg = df_gpr_plot.rolling(12).mean()
df_gpr_mavg = df_gpr_mavg.dropna()





#%% figures


# Set font family globally
plt.rcParams['font.family'] = 'Geneva'

# define initial color scheme for all graphs
init_color = 'Set2'

# define other parameters
line_width = 4
xpad = 10
ypad = 5
title_pad = 12

# country colors
can_color = '#C91D42'
usa_color = '#1DC9A4'
gbr_color = '#1DC9A4'
jpn_color = '#E1DFD0'
deu_color = '#595959'
fra_color = '#1F2E7A'
itl_color = '#D0E1E1'

# (1) total assets anywhere 
fig, ax = plt.subplots(figsize=(8,5))
df_totalinv.drop(columns='United States').plot(ax=ax,
                 lw=4,
                 alpha=0.4,
                 colormap=init_color)
# always make Canada red
for line in ax.get_lines():
    if line.get_label() == 'Canada':
        line.set_color(can_color)
        line.set_alpha(1)
    if line.get_label() == 'United States':
        line.set_color(usa_color)
        line.set_alpha(0.35)
    if line.get_label() == 'United Kingdom':
        line.set_color(gbr_color)
        line.set_alpha(0.35)
    if line.get_label() == 'Japan':
        line.set_color(jpn_color)
        line.set_alpha(0.6)
    if line.get_label() == 'Germany':
        line.set_color(deu_color)
        line.set_alpha(0.35)
    if line.get_label() == 'France':
        line.set_color(fra_color)
        line.set_alpha(0.35)
    if line.get_label() == 'Italy':
        line.set_color(itl_color)
        line.set_alpha(1)
# plot
plt.legend(fontsize=8, framealpha=1, borderpad=0.75)
plt.grid(color = 'gray', axis='y', linestyle = '--', linewidth = 0.5)
plt.suptitle("Total assets issued abroad (foreign assets)", x=0.35, y=1, fontsize=14, fontweight='heavy')
plt.title("Trillions of USD", x=0.047, y=1.035, fontsize=10)
plt.xlabel("Year", labelpad=xpad)
#plt.ylabel("Tot. Foreign Assets, trillions of USD", labelpad=ypad)
ax.text(x=0.1, y=-0.03, s="""Source: IMF Coordinated Portfolio Investment Survey""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_xticklabels(df_share_in_china.index.get_level_values(0))
plt.show()
fig.savefig(os.path.join(output_path, "total_foreign_assets.png"), dpi=300, bbox_inches='tight')



# (2) total assets in China
fig, ax = plt.subplots(figsize=(8,5))
df_inv_in_china.drop(columns='United States').plot(ax=ax,
                     lw=4,
                     alpha=0.4,
                     colormap=init_color)
# always make Canada red
for line in ax.get_lines():
    if line.get_label() == 'Canada':
        line.set_color(can_color)
        line.set_alpha(1)
    if line.get_label() == 'United States':
        line.set_color(usa_color)
        line.set_alpha(0.35)
    if line.get_label() == 'United Kingdom':
        line.set_color(gbr_color)
        line.set_alpha(0.35)
    if line.get_label() == 'Japan':
        line.set_color(jpn_color)
        line.set_alpha(0.6)
    if line.get_label() == 'Germany':
        line.set_color(deu_color)
        line.set_alpha(0.35)
    if line.get_label() == 'France':
        line.set_color(fra_color)
        line.set_alpha(0.35)
    if line.get_label() == 'Italy':
        line.set_color(itl_color)
        line.set_alpha(1)
# plot
plt.legend(fontsize=8, framealpha=1, borderpad=0.75)
plt.grid(color = 'gray', axis='y', linestyle = '--', linewidth = 0.5)
plt.suptitle("Investment in Chinese assets", x=0.252, y=1, fontsize=14, fontweight='heavy')
plt.title("Billions of USD", x=0.021, y=1.035, fontsize=10)
plt.xlabel("Year", labelpad=xpad)
#plt.ylabel("Assets, billions of USD", labelpad=ypad)
ax.text(x=0.08, y=-0.03, s="""Source: IMF Coordinated Portfolio Investment Survey""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_xticklabels(df_share_in_china.index.get_level_values(0))
plt.show()
fig.savefig(os.path.join(output_path, "chinese_assets.png"), dpi=300, bbox_inches='tight')



# (3) share of assets in China
fig, ax = plt.subplots(figsize=(8,5))
df_share_in_china.drop(columns='United Kingdom').plot(ax=ax,
                       lw=4,
                       alpha=0.4,
                       colormap=init_color)
# always make Canada red
for line in ax.get_lines():
    if line.get_label() == 'Canada':
        line.set_color(can_color)
        line.set_alpha(1)
    if line.get_label() == 'United States':
        line.set_color(usa_color)
        line.set_alpha(0.35)
    if line.get_label() == 'United Kingdom':
        line.set_color(gbr_color)
        line.set_alpha(0.35)
    if line.get_label() == 'Japan':
        line.set_color(jpn_color)
        line.set_alpha(0.6)
    if line.get_label() == 'Germany':
        line.set_color(deu_color)
        line.set_alpha(0.35)
    if line.get_label() == 'France':
        line.set_color(fra_color)
        line.set_alpha(0.35)
    if line.get_label() == 'Italy':
        line.set_color(itl_color)
        line.set_alpha(1)
# plot      
plt.legend(fontsize=8, framealpha=1, borderpad=0.75)
plt.grid(color = 'gray', axis='y', linestyle = '--', linewidth = 0.5)
plt.suptitle("Share of foreign assets issued in China", x=0.315, y=1, fontsize=14, fontweight='heavy')
plt.title("% of foreign-issued assets", x=0.095, y=1.035, fontsize=10)
plt.xlabel("Year", labelpad=xpad)
#plt.ylabel("% of Foreign Assets", labelpad=ypad)
ax.text(x=0.084, y=-0.03, s="""Source: IMF Coordinated Portfolio Investment Survey""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_xticklabels(df_share_in_china.index.get_level_values(0))
plt.show()
fig.savefig(os.path.join(output_path, "share_of_foreign_assets_china.png"), dpi=300, bbox_inches='tight')



# bond holdings over time for Canada
fig, ax = plt.subplots(figsize=(8,5))
df_bond_holdings['Canada'].plot(ax=ax,
                                color=can_color,
                                lw=line_width)

ax.text(x=0.09, y=-0.01, s="""Source: OECD Global Pension Statistics""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.grid(color = 'gray', axis='y', linestyle = '--', linewidth = 0.5)
plt.suptitle("Bond holdings of Canadian pensions", x=0.3, y=1, fontsize=14, fontweight='heavy')
plt.title("% of assets", x=0.02, y=1.035, fontsize=10)
plt.xlabel("Year", labelpad=xpad)
#plt.ylabel("% of Assets", labelpad=ypad)
plt.show()
fig.savefig(os.path.join(output_path, "canada_bond_holdings.png"), dpi=300, bbox_inches='tight')




# cash holdings over time for Canada
fig, ax = plt.subplots(figsize=(8,5))
df_cash_holdings['Canada'].plot(ax=ax,
                                color=can_color,
                                lw=line_width)

ax.text(x=0.09, y=-0.01, s="""Source: OECD Global Pension Statistics""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_xticklabels(df_share_in_china.index.get_level_values(0))
plt.grid(color = 'gray', axis='y', linestyle = '--', linewidth = 0.5)
plt.suptitle("Cash holdings of Canadian pensions", x=0.3, y=1, fontsize=14, fontweight='heavy')
plt.title("% of assets", x=0.02, y=1.035, fontsize=10)
plt.xlabel("Year", labelpad=xpad)
#plt.ylabel("% of Assets", labelpad=ypad)
plt.show()
fig.savefig(os.path.join(output_path, "canada_cash_holdings.png"), dpi=300, bbox_inches='tight')





# China geopolitical risk, moving average
fig, ax = plt.subplots(figsize=(8,5))

df_gpr_mavg['GPRC_CHN'].plot(ax=ax,
                             color='#1F2E7A', # dark blue
                             lw=line_width)
df_gpr_mavg['GPRC_TWN'].plot(ax=ax,
                             color='#475ED1', # mid blue
                             lw=line_width)
df_gpr_mavg['GPRC_HKG'].plot(ax=ax,
                             color='#1DC9A4', # light blue
                             lw=line_width)

ax.text(x=0.08, y=-0.03, s="""Source: Matteo Iacoviello, personal website""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.legend(['China','Taiwan','Hong Kong'],framealpha=1, borderpad=0.6)
plt.grid(color = 'gray', axis='y', linestyle = '--', linewidth = 0.5)
plt.suptitle("Caldara-Iacoviello GPR index", x=0.245, y=1, fontsize=14, fontweight='heavy')
plt.title("% of articles mentioning adverse events", x=0.163, y=1.035, fontsize=10)
plt.xlabel("Year", labelpad=xpad)
#plt.ylabel("% of Articles", labelpad=ypad)
plt.show()
fig.savefig(os.path.join(output_path, "geopolitical_risk_index_china.png"), dpi=300, bbox_inches='tight')




# total pension assets as percent of GDP over time
fig, ax = plt.subplots(figsize=(8,5))
df_pens_gdp_clean[['Canada']].plot(ax=ax,
                                   lw=line_width,
                                   alpha=0.4,
                                   colormap=init_color)
# always make Canada red
for line in ax.get_lines():
    if line.get_label() == 'Canada':
        line.set_color(can_color)
        line.set_alpha(1)
# plot
plt.legend('',frameon=False)
plt.grid(color = 'gray', axis='y', linestyle = '--', linewidth = 0.5)
plt.suptitle("Canadian pension assets as % of GDP", x=0.3, y=0.965, fontsize=14, fontweight='black')
plt.xlabel("Year", labelpad=xpad)
#plt.ylabel("% of GDP", labelpad=ypad)
ax.text(x=0.08, y=-0.01, s="""Source: OECD Global Pension Statistics""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.show()
fig.savefig(os.path.join(output_path, "\canada_pension_assets_perc_gdp.png"), dpi=300, bbox_inches='tight')



    

# pension asset structure for various countries (bar charts)
fig, ax = plt.subplots(figsize=(8,5))
df_g7_assets_2021.plot(ax=ax,
                       x = 'country',
                       kind = 'barh',
                       stacked = True,
                       mark_right = True,
                       edgecolor = 'black',
                       linewidth = 0.2,
                       color=['#141F52','#D6DBF5','#475ED1','#D2F9F0','#1DC9A4'])

# set bar colors
plt.suptitle("% of pension allocation", x=0.258, y=1.04, fontsize=14, fontweight='black')
plt.legend(ncol=5, loc=(0, 1.05), columnspacing=0.8)
plt.ylabel("", labelpad=0)
ax.text(x=0.12, y=0, s="""Source: OECD Global Pension Statistics""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.text(x=0.12, y=-0.03, s="""*Only classes of non-mutual fund holdings are shown""", transform=fig.transFigure, ha='left', fontsize=9, alpha=.7)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.yaxis.tick_right()
ax.tick_params(axis=u'both', which=u'both', length=0)
ax.tick_params(axis='y', pad=-10)
plt.show()
fig.savefig(os.path.join(output_path, "pension_asset_structure_2021.png"), dpi=300, bbox_inches='tight')


    




#%% depracated

# =============================================================================
# 
# # China geopolitical risk
# fig, ax = plt.subplots(figsize=(8,5))
# 
# # China, Mainland
# df_gpr_plot = df_gpr
# df_gpr_plot = df_gpr_plot.set_index('month')
# df_gpr_plot = df_gpr_plot[~df_gpr_plot['GPRC_CHN'].isna()]
# df_gpr_plot = df_gpr_plot[df_gpr_plot.index >= pd.Timestamp('1993-01-01')]
# df_gpr_plot['GPRC_CHN'].plot(ax=ax, lw=2)
# 
# # Hong Kong
# df_gpr_plot = df_gpr
# df_gpr_plot = df_gpr_plot.set_index('month')
# df_gpr_plot = df_gpr_plot[~df_gpr_plot['GPRC_HKG'].isna()]
# df_gpr_plot = df_gpr_plot[df_gpr_plot.index >= pd.Timestamp('1993-01-01')]
# df_gpr_plot['GPRC_HKG'].plot(ax=ax, lw=2)
# 
#  # Taiwan
# df_gpr_plot = df_gpr
# df_gpr_plot = df_gpr_plot.set_index('month')
# df_gpr_plot = df_gpr_plot[~df_gpr_plot['GPRC_TWN'].isna()]
# df_gpr_plot = df_gpr_plot[df_gpr_plot.index >= pd.Timestamp('1993-01-01')]
# df_gpr_plot['GPRC_TWN'].plot(ax=ax, lw=2)
# 
# plt.grid(color = 'gray', linestyle = '--', linewidth = 0.5)
# plt.title("Caldara-Iacoviello GPR Index", pad=title_pad)
# plt.xlabel("Year", labelpad=xpad)
# plt.ylabel("% of Articles", labelpad=ypad)
# plt.show()
# 
# 
# =============================================================================
