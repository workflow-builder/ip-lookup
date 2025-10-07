# ip-lookup
simple Python script that takes a list of IPs or DNS names and outputs the owner and region information.

Features:

Accepts both IP addresses and DNS names as input
Automatically resolves DNS names to IPs
Outputs owner (organization) and region (location) for each entry
Saves results to an output file

usage:
clone this respository
```
python ip_lookup.py input.txt output.txt
```

Input file format (one per line):
```
8.8.8.8
google.com
1.1.1.1
cloudflare.com
```

The script will:

Read your list of IPs/DNS names
Resolve any DNS names to IP addresses
Look up owner and region information using a free API
Display progress in the console
Save formatted results to the output file
