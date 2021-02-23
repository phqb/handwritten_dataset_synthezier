#!/usr/bin/python3

from os import listdir
from os.path import isfile, join, basename, splitext
from random import seed, random, randint 
from subprocess import run

bills_dir = "bills"
signs_dir = "genuine_transparent"
outdir = "synthesized_2"
dataset_fname = "dataset.csv"
cloud_storage_prefix = "gs://phqb-automl-data/img/"
fuzzy_deg = 20
sign_w_min = 150
sign_w_max = 200
sign_w_fuzzy = 10
temp_file = "tmp.png"

existing_annotations = {
    "2728cmr": [
        [[387, 962], [387 + 89, 962 + 113]],
        [[531, 987], [531 + 78, 987 + 78]]
    ],
    "226716_cmr": [
        [[81, 861], [81 + 159, 861 + 92]],
        [[299, 874], [299 + 200, 874 + 79]]
    ],
    "Ahola-1": [
        [[384, 1067], [384 + 139, 1067 + 42]],
        [[502, 1016], [502 + 222, 1016 + 90]]
    ],
    "Ahola-pod-416776": [
        [[110, 914], [110 + 205, 914 + 77]],
        [[329, 912], [329 + 151, 912 + 88]]
    ],
    "HWL_200953_001": [
        [[283, 865], [283 + 149, 865 + 82]]
    ],
    "HWL_200953_003": [
        [[333, 980], [333 + 113, 980 + 83]],
        [[505, 980], [505 + 170, 980 + 81]]
    ]
}

def basename_wo_ext(f):
    return splitext(basename(f))[0]

def get_image_size(f):
    result = run(["identify", "-format", "%w %h", f], capture_output=True)
    stdout = result.stdout.decode()
    dim = stdout.split()
    return [int(dim[0]), int(dim[1])]

def fuzzy_dim(dim):
    [[left,top], [right,bottom]] = dim
    left += 2*random()*sign_w_fuzzy - sign_w_fuzzy
    top += 2*random()*sign_w_fuzzy - sign_w_fuzzy
    right += 2*random()*sign_w_fuzzy - sign_w_fuzzy
    bottom += 2*random()*sign_w_fuzzy - sign_w_fuzzy
    return [[left,top], [right,bottom]]

def normalize_dim(dim, w, h):
    [[left,top], [right,bottom]] = dim
    left /= w
    top /= h
    right /= w
    bottom /= h 
    return [[left,top], [right,bottom]]

def fuzzy_existing_annotations(bill_bn, bill_size, sign_bn):
    out_fname = "{}/{}__{}.jpg".format(outdir, bill_bn, sign_bn)
    dims = [ normalize_dim(fuzzy_dim(dim), bill_size[0], bill_size[1]) for dim in existing_annotations[bill_bn] ]

    return ["UNASSIGNED,{}{},Signature,{},{},,,{},{},,".format(
        cloud_storage_prefix,
        out_fname,
        left_normalized,
        top_normalized,
        right_normalized,
        bottom_normalized
    ) for [[left_normalized,top_normalized],[right_normalized,bottom_normalized]] in dims]

def synthesize(sign, sign_bn, sign_size, bill, bill_bn, bill_size):
    sign_resized_w = randint(sign_w_min, sign_w_max)
    sign_resized_h = int(sign_size[1] * sign_resized_w / sign_size[0])
    deg = int(2*random()*fuzzy_deg - fuzzy_deg)

    run(["convert", sign, "-background", "none", "-resize", "{}x{}".format(sign_resized_w, sign_resized_h), "-rotate", str(deg), temp_file])
    [sign_rotated_w, sign_rotated_h] = get_image_size(temp_file) 

    left = randint(0, bill_size[0] - sign_rotated_w)
    top = randint(0, bill_size[1] - sign_rotated_h)
    right = left + sign_rotated_w
    bottom = top + sign_rotated_h

    out_fname = "{}/{}__{}.jpg".format(outdir, bill_bn, sign_bn)

    run(["convert", bill, temp_file, "-geometry", "+{}+{}".format(left, top), "-composite", out_fname])

    left_normalized = round(left / bill_size[0], 3)
    top_normalized = round(top / bill_size[1], 3)
    right_normalized = round(right / bill_size[0], 3)
    bottom_normalized = round(bottom / bill_size[1], 3)

    return ["UNASSIGNED,{}{},Signature,{},{},,,{},{},,".format(
        cloud_storage_prefix,
        out_fname,
        left_normalized,
        top_normalized,
        right_normalized,
        bottom_normalized
    )] + fuzzy_existing_annotations(bill_bn, bill_size, sign_bn)

bills = [join(bills_dir, f) for f in listdir(bills_dir)]
bills = [f for f in bills if isfile(f)]
bills = [(f, basename_wo_ext(f), get_image_size(f)) for f in bills]

signs = [join(signs_dir, f) for f in listdir(signs_dir)]
signs = [f for f in signs if isfile(f)]
signs = [(f, basename_wo_ext(f), get_image_size(f)) for f in signs]

seed()

dataset = []
n = len(bills) * len(signs)
i = 0
last_percent = 0

for (bill, bill_bn, bill_size) in bills:
    for (sign, sign_bn, sign_size) in signs:
        dataset += synthesize(sign, sign_bn, sign_size, bill, bill_bn, bill_size)
        i += 1

        percent = int(100*i/n)
        if percent > last_percent:
            print("{}%".format(percent))
            last_percent = percent

run(["rm", temp_file])

with open(dataset_fname, "w") as f:
    for e in dataset:
        f.write(e)
        f.write("\n")
