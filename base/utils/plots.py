#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Utility functions for generating plots for use within templates

"""
import plotly
import plotly.graph_objs as go
import plotly.figure_factory as ff

import numpy as np


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
    #fig.data[0]['histnorm'] = 'probability'


    plot = plotly.offline.plot(fig,
                               output_type='div',
                               include_plotlyjs=False,
                               show_link=False,
                               config={"displayModeBar": False})
    return plot

