# Changelog

## 0.1.0 (unreleased)

First release.

- Parsers: Steam purchase history, Google Play order history, Humble Bundle orders, Amazon "Your Orders" export,
  PlayStation Store receipt emails.
- Browser exporters (userscript or console) for Steam, Google Play and Humble Bundle, which produce the files the
  parsers read from your own logged-in session.
- `parser(name)` resolver: built-in names or dotted paths to your own parsers.
