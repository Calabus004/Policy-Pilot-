"""
Step 1: A test list of fictional company and individual names, representing
a typical UK/EU fintech's customer base.

These are entirely made up for testing the pipeline end-to-end — none of
them correspond to real people or organisations. In production you would
replace this with a query against your real customer/KYC database, pulling
only the fields you actually need (name + entity type) for screening.

"schema" tells the OpenSanctions API what kind of entity this is, so it can
match against the right fields — use "Person" for individuals and "Company"
for organisations.
"""

TEST_NAMES = [
    # --- Fictional companies -------------------------------------------------
    {"name": "Meridian Payments Ltd", "schema": "Company"},
    {"name": "Northbridge Fintech Solutions", "schema": "Company"},
    {"name": "Alderney Digital Assets Ltd", "schema": "Company"},
    {"name": "Solstice Capital Partners", "schema": "Company"},
    {"name": "Kestrel Merchant Services", "schema": "Company"},
    {"name": "BluePeak Remittance Group", "schema": "Company"},
    {"name": "Ferrous Trade Finance Ltd", "schema": "Company"},
    {"name": "Hallow Point Ventures", "schema": "Company"},
    {"name": "Silverline Neobank Ltd", "schema": "Company"},
    {"name": "Aurica Crypto Exchange Ltd", "schema": "Company"},
    # --- Fictional individuals -----------------------------------------------
    {"name": "Daniel Ashworth", "schema": "Person"},
    {"name": "Priya Chandrasekaran", "schema": "Person"},
    {"name": "Marek Nowicki", "schema": "Person"},
    {"name": "Freya Lindqvist", "schema": "Person"},
    {"name": "Tobias Herrmann", "schema": "Person"},
    {"name": "Amara Okafor", "schema": "Person"},
    {"name": "Lucia Ferraro", "schema": "Person"},
    {"name": "Callum Mackenzie", "schema": "Person"},
    {"name": "Ingrid Vasquez", "schema": "Person"},
    {"name": "Ravi Deshmukh", "schema": "Person"},
]
