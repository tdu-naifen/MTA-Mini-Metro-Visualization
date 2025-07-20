#!/bin/bash

# Generate Thrift schemas for Python and TypeScript
echo "Generating Thrift schemas..."

# Create output directories
mkdir -p backend/generated
mkdir -p frontend/src/app/generated

# Generate Python classes
thrift -r --gen py -out backend/generated schemas/mta_data.thrift

# Generate TypeScript/JavaScript classes
thrift -r --gen js:ts -out frontend/src/app/generated schemas/mta_data.thrift

echo "Thrift schema generation complete!"
