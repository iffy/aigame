/*

All of these "facts" are from the perspective of Gary.  They may not be
objectively true, but they are subjectively true to him.

*/

is_stealing(take(Taker, Thing)) :-
    \+(owns(Taker, Thing)),
    (
        \+(has_perm(Owner, take(Taker, Thing))),
        owns(Owner, Thing)
    ).

morality(X, -1) :- is_stealing(X).


/* Verbal permission */
has_perm(Permitter, Action) :-
    said(Permitter, allowed(Action)).

/* Written permission */
has_perm(Permitter, Action) :-
    contains(Document, allowed(Action)),
    signed(Permitter, Document).


/* ---------------------------------- */

owns(bob, car).

/* verbal permission */
said(bob, allowed(take(alice, car))).

contains(legitcontract, allowed(take(fonz, car))).
contains(unsigned_contract, allowed(take(arnold, car))).
contains(bad_contract, allowed(take(yolanda, car))).

signed(bob, legitcontract).
signed(yolanda, bad_contract).

/*

Queries
is_stealing(take(jim, car)).
is_stealing(take(bob, car)).
is_stealing(take(alice, car)).
is_stealing(take(fonz, car)).
is_stealing(take(arnold, car)).
is_stealing(take(yolanda, car)).

morality(take(jim, car), X).
morality(take(bob, car), X).
morality(take(alice, car), X).
morality(take(fonz, car), X).
morality(take(arnold, car), X).
morality(take(yolanda, car), X).

*/
