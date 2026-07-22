"""The seed corpus — a small, curated set of UK VAT guidance excerpts.

Deliberately small but real: each entry cites an actual HMRC/legislation reference, and the
references match those the VAT engine already emits (VATDSAG, VATA 1994 Sch.8/9, etc.), so
a figure's authority in a return and the answer in the knowledge base point at the same
sources. This is illustrative, not a complete corpus — the honest scope stated in the
README — but the retrieval, citation, and refusal machinery it exercises is the real thing.

Passages are paraphrased summaries for demonstration, not verbatim Crown copyright text.
"""

from datetime import date

# (authority_rank, source, citation_ref, title, tax_domain, url, [(heading, body), ...])
CORPUS: list[tuple] = [
    (
        "A3",
        "hmrc_notice",
        "VAT Notice 700 §10",
        "VAT guide: input tax and its recovery",
        "VAT",
        "https://www.gov.uk/guidance/vat-guide-notice-700",
        [
            (
                "Recovering input tax",
                "A business may recover input tax it incurs on purchases used to make "
                "taxable supplies. Input tax attributable to exempt supplies is generally "
                "not recoverable, and where a business makes both taxable and exempt "
                "supplies it is partly exempt and must apportion its input tax.",
            ),
            (
                "Evidence for a claim",
                "To recover input tax a business must normally hold a valid VAT invoice "
                "showing the supplier's VAT registration number, the amount of VAT, and a "
                "description of the goods or services. Without valid evidence the claim may "
                "be refused.",
            ),
        ],
    ),
    (
        "A3",
        "hmrc_notice",
        "VATDSAG",
        "Domestic reverse charge for building and construction services",
        "VAT",
        "https://www.gov.uk/guidance/vat-domestic-reverse-charge-for-building-and-construction-services",
        [
            (
                "How the reverse charge works",
                "Under the domestic reverse charge, the customer receiving the supply of "
                "specified construction services accounts for the VAT due to HMRC instead of "
                "the supplier. The customer records the output tax on the supply and, subject "
                "to the normal rules, recovers it as input tax on the same return. The net "
                "cash effect is nil but both entries must appear.",
            ),
            (
                "When it applies",
                "The reverse charge applies to specified services between VAT-registered "
                "businesses where the customer is not the end user. The supplier does not "
                "charge VAT on the invoice; the invoice must state that the reverse charge "
                "applies and that the customer must account for the VAT.",
            ),
        ],
    ),
    (
        "A1",
        "legislation",
        "VATA 1994 Sch.9",
        "Value Added Tax Act 1994, Schedule 9 — exempt supplies",
        "VAT",
        "https://www.legislation.gov.uk/ukpga/1994/23/schedule/9",
        [
            (
                "Exempt supplies",
                "Certain supplies are exempt from VAT, including specified financial "
                "services, insurance, education provided by eligible bodies, and health and "
                "welfare services. An exempt supply is not a taxable supply: no VAT is "
                "charged and input tax attributable to it is not recoverable.",
            ),
        ],
    ),
    (
        "A1",
        "legislation",
        "VATA 1994 Sch.8",
        "Value Added Tax Act 1994, Schedule 8 — zero-rated supplies",
        "VAT",
        "https://www.legislation.gov.uk/ukpga/1994/23/schedule/8",
        [
            (
                "Zero-rated supplies",
                "Zero-rated supplies are taxable supplies on which VAT is charged at 0%. "
                "Because they are taxable, input tax attributable to making them is "
                "recoverable — the key distinction from exempt supplies. Zero-rated "
                "categories include most food, books and printed matter, and children's "
                "clothing.",
            ),
        ],
    ),
    (
        "A3",
        "hmrc_manual",
        "VIT13500",
        "VAT input tax: staff entertainment and hospitality",
        "VAT",
        "https://www.gov.uk/hmrc-internal-manuals/vat-input-tax/vit13500",
        [
            (
                "Business entertainment",
                "VAT incurred on business entertainment provided to non-employees is "
                "generally blocked and cannot be recovered. VAT on entertainment provided "
                "wholly for employees, such as a staff party, may be recovered as input tax, "
                "though a private-use restriction can apply where guests attend.",
            ),
        ],
    ),
    (
        "A3",
        "hmrc_notice",
        "VAT Notice 700/12",
        "How to fill in and submit your VAT Return",
        "VAT",
        "https://www.gov.uk/guidance/how-to-fill-in-and-submit-your-vat-return-vat-notice-70012",
        [
            (
                "Box 1 and Box 4",
                "Box 1 shows the VAT due on sales and other outputs. Box 4 shows the VAT "
                "reclaimed on purchases and other inputs. Box 5 is the net VAT to pay or "
                "reclaim, calculated as the difference between Box 3 (total VAT due) and "
                "Box 4.",
            ),
            (
                "Boxes 6 and 7",
                "Box 6 is the total value of sales and other outputs excluding VAT. Box 7 is "
                "the total value of purchases and other inputs excluding VAT. These figures "
                "are rounded to whole pounds.",
            ),
        ],
    ),
]

DEFAULT_VALID_FROM = date(2021, 3, 1)  # reverse-charge rules effective date, a sensible floor
