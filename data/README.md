# Fixed Inside Airbnb snapshot

The full rerun uses the Greater Manchester snapshot dated **28 June 2026** from
[Inside Airbnb's data archive](https://insideairbnb.com/get-the-data/). Download
these files into this directory without renaming them:

| Local file | Exact source | SHA-256 |
|---|---|---|
| `listings.csv` | [summary listings](https://data.insideairbnb.com/united-kingdom/england/greater-manchester/2026-06-28/visualisations/listings.csv) | `c263f67fa2c800aa1cd48815b3ff23a5b21eae1a243e11d5d0a25d82ccbcd41e` |
| `listings.csv.gz` | [detailed listings](https://data.insideairbnb.com/united-kingdom/england/greater-manchester/2026-06-28/data/listings.csv.gz) | `979c31471f67ec5f6dbd1d94b298eb01f3708722cf102d94df2feef26d10334c` |
| `reviews.csv.gz` | [review text](https://data.insideairbnb.com/united-kingdom/england/greater-manchester/2026-06-28/data/reviews.csv.gz) | `d08a26d4d61f9c67283933013a4223a14f169e5cf0ee1bd98156c0a85411da73` |

`listings.csv` is the 6,947-row inventory. Review text is in `reviews.csv.gz`,
joined by `reviews.listing_id = listings.id`. The detailed listing file has
6,930 rows and supplies additional metadata. The notebook reports every sample
coverage figure against either the 6,947-listing inventory or the 5,579 reviewed
listing population and labels the denominator.

The downloaded files are intentionally excluded from Git. The notebook checks
all three hashes before constructing a live request. The snapshot date is
28 June 2026; the sampling recency anchor is 29 June 2026.
