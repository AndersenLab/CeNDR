#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Utility functions for generating plots for use within templates

"""
import datetime
import plotly
import plotly.graph_objs as go
import plotly.figure_factory as ff
import plotly.graph_objs as go

import numpy as np
import pandas as pd


def to_unix_time(dt):
    """
        Convenience function for conversion to timestamp
    """
    epoch =  datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds() * 1000


def plotly_distplot(df, column):
    """Creates a Histogram

        The function will produce a distplot for displaying
        on reports. The distplot

        Args:
            labels - Data labels
            data - A Numpy Series to be plotted
    """
    df = df[['STRAIN', column]].dropna(how='any').sort_values([column])
    print(df)
    labels = df['STRAIN']
    data = df[column]

    # Plotly does not do a very good job calculating bin-size,
    # so we will have to help it out here.
    x, y = np.histogram(data, bins='auto')
    bin_size = y[1] - y[0]
    fig = ff.create_distplot([data],
                             [data.name],
                             bin_size=bin_size,
                             histnorm='probability')

    # Update axis labels
    fig['layout']['yaxis1']['title'] = "Pr(x)"
    fig['layout']['xaxis1']['title'] = data.name
    fig['layout']['showlegend'] = False
    fig['layout']['margin'] = {'t': 0, 'r': 0, 'l': 80, 'b': 60}
    fig.data[0]['hoverinfo'] = 'x+y'
    fig.data[1]['hoverinfo'] = 'x+y'
    fig.data[2]['text'] = labels
    fig.data[2]['hoverinfo'] = 'x+text'


    plot = plotly.offline.plot(fig,
                               output_type='div',
                               include_plotlyjs=False,
                               show_link=False,
                               config={"displayModeBar": False})
    return plot


def time_series_strain_isotype_plot(df):
    """
        Create a time-series plot of strains and isotypes collected over time

        Args:
            df - the strain dataset
    """
    cumulative_isotype = df[['isotype', 'isolation_date']].sort_values(['isolation_date'], axis=0) \
                                                          .drop_duplicates(['isotype']) \
                                                          .groupby(['isolation_date'], as_index=True) \
                                                          .count() \
                                                          .cumsum() \
                                                          .reset_index()
    cumulative_isotype = cumulative_isotype.append({'isolation_date': np.datetime64(datetime.datetime.today().strftime("%Y-%m-%d")),
                                                    'isotype': len(df['isotype'].unique())}, ignore_index=True)
    cumulative_strain = df[['strain', 'isolation_date']].sort_values(['isolation_date'], axis=0) \
                                                        .drop_duplicates(['strain']) \
                                                        .dropna(how='any') \
                                                        .groupby(['isolation_date']) \
                                                        .count() \
                                                        .cumsum() \
                                                        .reset_index()
    cumulative_strain = cumulative_strain.append({'isolation_date': np.datetime64(datetime.datetime.today().strftime("%Y-%m-%d")),
                                                  'strain': len(df['strain'].unique())}, ignore_index=True)
    df = cumulative_isotype.set_index('isolation_date') \
                           .join(cumulative_strain.set_index('isolation_date')) \
                           .reset_index()

    trace_set = []
    for column in df.columns[1:][::-1]:
        trace_set.append(go.Scatter(
                                    x=df[df.columns[0]],
                                    y=df[column],
                                    name=column,
                                    opacity=0.8
                                    )
                        )

    layout = go.Layout(xaxis=dict(range=[datetime.datetime(1995, 10, 17),
                                         datetime.datetime.today()],
                                  title='Year'),
                       yaxis=dict(title='Count'),
                       margin={'t': 0, 'r': 0, 'l': 80, 'b': 60},
                       )

    fig = go.Figure(data=trace_set, layout=layout)
    return plotly.offline.plot(fig,
                               output_type='div',
                               include_plotlyjs=False,
                               show_link=False,
                               config={"displayModeBar": False})
