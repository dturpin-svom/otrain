#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: David Corre, IAP, corre@iap.fr

"""

import sys

import glob
import re
import os
import errno
import numpy as np
from astropy.io import fits
import argparse
from tbd_cnn.utils import rm_p, mkdir_p
from math import floor


def convert(path_datacube, cubename, path_cutouts, frac_true):
    """Convert simulated data before starting training"""

    # outdir = os.path.join(path_datacube, "datacube")
    outdir = path_datacube
    mkdir_p(outdir)

    # Get all the prefixes corresponding to one field
    truelist = glob.glob(os.path.join(path_cutouts, "true", "*.fits"))
    falselist = glob.glob(os.path.join(path_cutouts, "false", "*.fits"))
    # output cube name
    npz_name = "%s.npz" % cubename
    Ncand_true = len(truelist)
    Ncand_false = len(falselist)
    if Ncand_true > Ncand_false:
        Ncand_true_max = floor(2 * Ncand_false * frac_true)
        Ncand_false_max = floor(2 * Ncand_false * (1 - frac_true))
    elif Ncand_true <= Ncand_false:
        Ncand_true_max = floor(2 * Ncand_true * frac_true)
        Ncand_false_max = floor(2 * Ncand_true * (1 - frac_true))

    Ncand_tot = len(truelist) + len(falselist)
    Ncand = Ncand_true_max + Ncand_false_max
    cube = []  # np.zeros((Ncand, 64, 64))
    labels = []
    mags = []
    errmags = []
    cand_ids = []
    filters = []
    counter_true = 0
    for cand in truelist:
        if counter_true < Ncand_true_max:
            hdus = fits.open(cand, memmap=False)
            head = hdus[0].header
            # Exclude cases too close to the edge
            # Meaning they are located at less than the defined size
            # of the small images
            if head["EDGE"] == "False":
                labels += [1]
                mags += [head["MAG"]]
                errmags += [head["MAGERR"]]
                filters += [head["FILTER"]]
                cand_ids += [head["CANDID"]]
                cube.append(hdus[0].data)
            hdus.close()
        else:
            break
        counter_true = counter_true + 1

    counter_false = 0
    for cand in falselist:
        if counter_false < Ncand_false_max:
            hdus = fits.open(cand, memmap=False)
            head = hdus[0].header
            # if hdus[0].data.shape != (64, 64):
            #    print ('skip %s as its shape is not (64,64): (%d,%d)'
            #           % (cand, hdus[0].data.shape[0], hdus[0].data.shape[1]))
            # Exclude cases too close to the edge
            # Meaning they are located at less than the defined size
            # of the small images
            if head["EDGE"] == "False":
                labels += [0]
                mags += [head["MAG"]]
                errmags += [head["MAGERR"]]
                filters += [head["FILTER"]]
                cand_ids += [head["CANDID"]]
                cube.append(hdus[0].data)
            hdus.close()
        else:
            break
        counter_false = counter_false + 1

    print(
        "The datacube contains",
        str(Ncand),
        "candidates with Ntrue =",
        str(counter_true),
        "and Nfalse =",
        str(counter_false),
    )
    print("Converting and reshaping arrays ...")
    # Convert lists to B.I.P. NumPy arrays
    # Check whether all candidates has 64x64 pixels
    # If not, delete them
    # This can happen at the edge of images
    # for i in range(len(cube)):
    #    if np.array(cube[i]).shape != (64, 64):
    #        print (i, np.array(cube[i]).shape)
    #        del cube[i]
    cube = np.asarray(cube, dtype=np.float32)
    if cube.ndim < 4:
        cube = np.reshape(cube, [cube.shape[0], cube.shape[1], cube.shape[2], 1])
    else:
        cube = np.moveaxis(cube, 1, -1)

    # Report dimensions of the data cube
    print("Saving %d %d×%d×%d image datacube ..." % cube.shape, end="\r", flush=True)
    np.savez(
        os.path.join(outdir, npz_name),
        cube=cube,
        labels=labels,
        mags=mags,
        errmags=errmags,
        filters=filters,
        candids=cand_ids,
    )

    print("Saved to " + os.path.join(outdir, npz_name))
