#!/usr/bin/env bash
set -euo pipefail
cmake -S "${1:-.}" -B "${2:-build}" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ \
  -DBUILD_MODULE_ApplicationFramework=OFF -DBUILD_MODULE_DataExchange=OFF \
  -DBUILD_MODULE_Draw=OFF -DBUILD_MODULE_FoundationClasses=OFF \
  -DBUILD_MODULE_ModelingAlgorithms=OFF -DBUILD_MODULE_ModelingData=OFF \
  -DBUILD_MODULE_Visualization=OFF '-DBUILD_ADDITIONAL_TOOLKITS=TKPrim' \
  -DUSE_FREETYPE=OFF -DUSE_TK=OFF
cmake --build "${2:-build}" --parallel 2 --target TKPrim