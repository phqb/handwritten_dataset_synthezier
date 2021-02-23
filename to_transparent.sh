#!/bin/sh

cd genuine

for img in *.PNG; do
  convert ${img} -fuzz 10% -transparent white ../genuine_transparent/${img}
done
