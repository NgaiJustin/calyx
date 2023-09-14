# VCalyx

## Parsing a single file

Install flit:

    python3 -m pip install flit

In the `fud` directory, run:

    flit install --symlink

Register the external VCalyx stage:

    fud register vcalyx -p fud/fud/stages/vcalyx.py

Finally, run the `fud` command:

    fud e <path/to/futil> --to vcx 

To obtain the S-expression form of a Calyx program, run:

    fud e <path/to/futil> --to vcalyx 

## Running the test suite

Install runt:

    cargo install runt

In the `vcalyx` directory, run:

    runt