# Balance sheet playground tool

## Context
- I work in investment bank in a fixed income trading department
- I often need to figure out how certain funding rules / PNL write down rules etc work
- To do this I have to draw balance sheets of different desks and how they change
- It's quite cumbersome and not too convenient to do it by hand, but very very representative and revealing
- I want to automate and ease this task


## TASK SPECS
---
### Task formulation
I need a tool for the following thing.
I want to build relatively small and simple balance sheets for different trading books for one or different depratments.
- The main goal of this is to have a convenient tool to represent different transactions & arising changes of balance sheets.
- Also the goal is to track changes of OCP in each book and PV of each book as different transactions happen and different market prices change (like FX levels or bonds quotes)

### Technical specs
- The tool should be able to accept steps of transactions (inside one day)
- After each step it should be able to draw chosen balance sheets (in some CLI mode), OCP in each balance sheet (in each CCY), PV of each book (in reporting currency)
- The transacitons should be easy to input (i.e. not too long to type, have some syntactic sugar)
- It should be possible (but not necessary) to assign a rate or a rule at which each asset / liability in each balance sheet accrues interest.
  - It might be written in abs rate terms or in a formula terms (like LIBOR+2%).
  - The main outcome - the system should then be able to calculate symbolic cost of running this balance sheet. Symbolic means the overall expression should be then simplified. It should be possible to:
    - Represent the resulting cost in simplified version (see more details below),
    - Enter the values of each symbolic parameter (like LIBOR = 0.5%) and then show the cost of running the balance sheet in numeric terms (see details below)

### Tech stack
1. There should be some underlying lib / protocol / language to record financial transactions. Can be beancount, or ledger, or just SQLite DB
2. There are 2 options i have in mind for transactions entering
   1. in some file in some format,
   2. or to have a python interface with some nice and easy to use ways of input
     1. IMPORTANT: the tool should be liteweight in terms of how to input transactions, i.e. if i want to see smthg quickly, i should be setup and do all the stuff in just a few lines / cpl of minutes.

### The use
The tool should be used / usable in Python. I want to have easy-to-setup-and-enter, yet powerful setup for:
- Setting up balance sheets & accounts
- Entering transactions
- Putting timestamps for transactions , so I can enter the whole ledger and then build balance sheets with different time stamps
- Inputting market data (interest rates / FX rates / assets prices)
- Seeing balance sheets state at certain date / time
- Calculating OCP, representing funding formula, calculating actual funding and PV

### Things to think about
Please reflect upon how will accrued interest / price changes be represented.
The main use case for the whole system - is to play with stuff to see how OCP changes, how funding changes, what the overall funding rates are

## REPRESENTATIONS / EXAMPLES
---
### Funding cost representation
- It should be possible to enter "interest cost" for each asset / liability. It can be in just % (like 5%, which's 5% annualized) or some symbolic value - like "RUONIA + 3%", where RUONIA is a RUB interest rate index

#### EXAMPLE
_Bear in mind the numbers might not be ideally correct, i've calculated them in my head, there might be mistakes_
_This example is for representation_

__The balance sheet consists of__
  Assets:
  - $ bond $30mm @ 7%
  - $ bond $50mm @ LIBOR + 2%
  - RUB bond 1bio RUB @ 15%
  - RUB bond 5bio RUB @ RUONIA + 3%
  Liabilities:
  - USD $60mm loan @ LIBOR + 1%
  - RUB 4bio loan @ RUONIA + 1%
  - The rest is equity (which depends on the FX rates, the base ccy is RUB, so it's deemed to be RUB)

__Simplification goal__
The simplification goal is to show


### Balance sheet representation
                                      BND
----------------------------------------------------------------------------------------
7%          @ USD 30mm # BOND1        | USD_LOAN1 # USD 60mm       @ LIBOR + 1%
LIBOR + 2%  @ USD 50mm # BOND2        | RUB_LOAN2 # RUB 4bio       @ RUONIA + 1%
15%         @ RUB 1bio # RUB_BOND1    | EQUITY    # RUB [3.6 bio]  @ 0%
RUONIA + 3% @ RUB 5bio # RUB_BOND2    |

------------------------
OCP: USD +20mm
PV:  3.6bio RUB
--- RATES ----
USDRUB @ 80.00
RUONIA @ 14%
LIBOR  @ 3.5%

INTEREST COST:
------- LEVEL 1 --------
USD 30mm   @ +7%
USD 50mm   @ +1%
(USD 10mm) @ LIBOR+1%
RUB 1bio   @ +15%
RUB 4bio   @ +2%
RUB 1bio   @ RUONIA+3%

------- LEVEL 2 -------- (calculated interest at known rates)
+USD 2.5mm
-USD 10mm * LIBOR
+RUB 230mm
+RUB 1bio * RUONIA

------- LEVEL 3 -------- (calculated wrt interest rate indices)
+USD 2.15mm
+RUB 370mm

------- LEVEL 4 -------- (calculated in RUB wrt all market data)
+RUB 542mm

**IMPORTANT:** The calculations might be incorrect. This is more a repersentation
and functionality example rather than the exact numbers example

### Transactions examples.

- There are 4 books - BND, DER, FX, TSY. BND & DER books belong to the same desk, other books each represent its own desk.
- BND book buys $ denominated bond, paying in RUB. 100 bonds @ 100.00% , FX rate = 80.00
- BND book has to fund bond in the same ccy as a bond ccy, so it sells $/RUB to DER book at some fx rate
- BND book has $ funding from TSY book vs the bond
- DER book has long USD, short RUB cash from the intrabook fx trade, it places USD cash in TSY vs borrows RUB cash from TSY
- TSY book is
  - -ve RUB cash vs having loan to DER book in rub
  - +ve USD cash vs having borrowing from DER bbok
  - USD loan to BND book to fund Bond

## More thoughts
I need a convenient and BEAUTIFUL tool. Please think of:
- Potentially better text representations of balance sheets
- Potential call arguments that will trigger showing or not showing certain things - like interest formuals, notionals, ccys etc. Also please consider setting up the representation (but wihtout a neeed to do it every time and with default values)
