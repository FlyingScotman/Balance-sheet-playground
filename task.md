# TASK Formulation

## General context
I want to create a tool that will help me to create toy balance sheets of an investment
bank's trading desk books.
The idea is this - i'll be creating small balance sheets of a book (say, FX book,
derivs book, treasury book, bonds trading book).
Each balance sheet will have a handful items as assets and liabilities -
- Bonds positions
- cash
- loans from tsy
- lending to tsy
and stuff like this.
The tool should be able to calculate:
- Open currency positions (OCP) of each balance sheet
- PV of a balance sheet (in the reporting ccy set)
- Also - it should be possible to set symbolic interest rate rules for each line
    - Then each line contains some formula like "LIBOR + 2%", or just "7.45%"
    - then, when we have symbolic formulas, it should be possible to
