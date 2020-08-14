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

import numpy as np
import pandas as pd

COLORS = ['rgba(93, 164, 214, 0.65)',
          'rgba(255, 65, 54, 0.65)',
          'rgba(207, 114, 255, 0.65)',
          'rgba(127, 96, 0, 0.65)']


def to_unix_time(dt):
    """
        Convenience function for conversion to timestamp
    """
    epoch = datetime.datetime.utcfromtimestamp(0)
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
    labels = df.STRAIN
    data = df[column]

    # Plotly does not do a very good job calculating bin-size,
    # so we will have to help it out here.
    x, y = np.histogram(data, bins='auto')
    bin_size = y[1] - y[0]
    fig = ff.create_distplot([data],
                             [data.name],
                             bin_size=bin_size,
                             histnorm='count',
                             show_curve=False)

    # Update axis labels
    fig['layout']['yaxis1']['title'] = "Count"
    fig['layout']['xaxis1']['title'] = data.name
    fig['layout']['showlegend'] = False
    fig['layout']['margin'] = {'t': 20, 'r': 0, 'l': 80, 'b': 80}
    fig.data[0]['hoverinfo'] = 'x+y'
    fig.data[1]['text'] = labels
    fig.data[1]['hoverinfo'] = 'x+text'

    plot = plotly.offline.plot(fig,
                               output_type='div',
                               include_plotlyjs=False,
                               show_link=False,
                               config={"displayModeBar": False})
    return plot


def time_series_plot(df, x_title=None, y_title=None, range=None, colors=COLORS):
    """
        Pass in a dataframe (df) with:
            First column - dates (x-axis)
            2nd, 3rd, 4th, etc. columns - values

        Args:
            df - the strain dataset
    """
    trace_set = []
    for n, column in enumerate(df.columns[1:][::-1]):
        trace_set.append(go.Scatter(x=df[df.columns[0]],
                                    y=df[column],
                                    name=column,
                                    opacity=0.8,
                                    line=dict(color=(COLORS[n]))
                                    )
                         )

    layout = go.Layout(margin={'t': 0, 'r': 0, 'l': 80, 'b': 60},
                       xaxis={})
    if range:
        layout['xaxis']['range'] = range
    if x_title:
        layout['xaxis']['title'] = x_title
    if y_title:
        layout['yaxis']['title'] = y_title

    fig = go.Figure(data=trace_set, layout=layout)
    return plotly.offline.plot(fig,
                               output_type='div',
                               include_plotlyjs=False,
                               show_link=False,
                               config={"displayModeBar": False})


def pxg_plot(df, trait_name):
    """
        Generates a phenotype x genotype plot

        Must be feed a dataframe with the markers and genotypes.

        Args:
            trait_name - The name of the trait (Y-axis)
    """
    peak_markers = set(df.MARKER)
    trace_set = []
    ticktext = []
    tickvals = []
    offset = 0.0
    df.GT = pd.Categorical(df.GT)
    for marker_n, marker in enumerate(peak_markers):
        mset = df[df.MARKER == marker]
        for gt_n, gt in enumerate(set(mset.GT)):
            x_coord = marker_n + gt_n + offset
            tickvals.append(x_coord)
            ticktext.append(gt)
            gset = mset[mset.GT == gt]
            gset = gset.assign(x=(marker_n + gt_n + offset)*1.0)
            gset = gset.assign(x_distr=gset.x + (np.random.standard_normal(len(gset.GT))/15)-0.75)
            trace = go.Box(
                name=marker+str(marker_n) + str(gt_n),
                y=gset.TRAIT,
                x=gset.x,
                xaxis='x1',
                yaxis='y1',
                hoverinfo="all",
                boxpoints='outlier',
                fillcolor=COLORS[gt_n],
                whiskerwidth=0.2,
                marker=dict(
                    color=COLORS[gt_n],
                    opacity=0.5
                ),
                line=dict(width=2)
            )
            trace_jitter = go.Scatter(
                y=gset.TRAIT,
                x=gset.x_distr,
                xaxis='x1',
                yaxis='y1',
                text=gset.STRAIN,
                hoverinfo="text+y",
                mode='markers',
                marker=dict(
                    color=COLORS[gt_n],
                    size=5,
                    opacity=0.8,
                    line=dict(width=1)
                ),
            )
            trace_set.append(trace)
            trace_set.append(trace_jitter)
            offset += 1

        # Add marker labels
        trace_marker_label = go.Scatter(name=marker,
                                        y=[1],
                                        x=[marker_n + offset-1],
                                        yaxis='y2',
                                        text=[marker],
                                        hoverinfo='none',
                                        mode='text',
                                        textposition='bottom',
                                        textfont=dict(
                                            family='courier',
                                            size=25
                                        )
                                        )
        trace_set.append(trace_marker_label)
        offset += 2.5

    layout = go.Layout(
        hovermode='closest',
        xaxis=dict(
            title="Genotype",
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext,
        ),
        yaxis1=dict(
            domain=[0, 0.7],
            title=trait_name
        ),
        yaxis2=dict(
            domain=[0.7, 1],
            visible=False
        ),
        margin=dict(
            l=80,
            r=80,
            b=80,
            t=0,
        ),
        showlegend=False
    )

    fig = go.Figure(data=trace_set, layout=layout)
    return plotly.offline.plot(fig,
                               output_type='div',
                               include_plotlyjs=False,
                               show_link=False,
                               config={"displayModeBar": False})


def fine_mapping_plot(df):
    pass


