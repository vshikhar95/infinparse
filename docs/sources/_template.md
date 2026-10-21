# <Source name>

## Source and parser
Institution or store, the parser (`importers/<name>`, `purchases/<name>` or `portfolio/<name>`) and the install extra it needs.

## Official site
A link to the institution's front page or help page, plus the menu path to the export (for example
"Statements → Download → XLS"). Front-page links plus clicks, because deep links break.

## How the file arrives
A portal download or a periodic email attachment. Name a sender as "the bank's statements email", never an address.

## What to pick
Format, date range, and any row or period limits.

## Password
The institution's published convention, described generically (for example "name prefix + date of birth, as the
statement email says"). Never a real value.

## What you get
The model returned and its sign convention; whether `meta()` supplies account-key placeholders.

## Assumptions and quirks
INR, English locale, date format, and layout dependencies.
