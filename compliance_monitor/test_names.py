"""
Step 1: A test list of company and individual names, representing a
typical UK/EU fintech's customer base.

Companies are real, publicly listed companies — real corporate names are
public record (Companies House / stock exchange filings, not personal
data), so there's no privacy issue using them here, and it lets you see
the OpenSanctions match API respond to genuine entities instead of names
it has never heard of. None of these companies are sanctioned; running
this script should produce zero matches for all of them, which is the
expected, boring, good outcome.

Individuals are entirely fictional — do not replace these with real
people's names. Screening a real private individual without their
knowledge/consent raises data protection issues (UK GDPR) that a public
company's name does not.

In production you would replace this whole list with a query against your
real customer/KYC database, pulling only the fields you actually need
(name + entity type) for screening — and you'd need a proper GDPR lawful
basis for screening real individuals, which this test script does not
attempt to establish.

"schema" tells the OpenSanctions API what kind of entity this is, so it can
match against the right fields — use "Person" for individuals and "Company"
for organisations.
"""

TEST_NAMES = [
    # --- Real, publicly listed companies (not sanctioned) --------------------
    {"name": "Tesco PLC", "schema": "Company"},
    {"name": "Vodafone Group Plc", "schema": "Company"},
    {"name": "BP p.l.c.", "schema": "Company"},
    {"name": "Unilever PLC", "schema": "Company"},
    {"name": "Barclays PLC", "schema": "Company"},
    {"name": "Rolls-Royce Holdings plc", "schema": "Company"},
    {"name": "AstraZeneca PLC", "schema": "Company"},
    {"name": "Diageo plc", "schema": "Company"},
    {"name": "BT Group plc", "schema": "Company"},
    {"name": "J Sainsbury plc", "schema": "Company"},
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
