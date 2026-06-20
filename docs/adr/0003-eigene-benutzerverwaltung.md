# ADR 0003 — Eigene Benutzerverwaltung, OIDC-fähig gebaut

**Status:** akzeptiert · **Datum:** 2026-06-20

## Kontext
Der Zugang muss geschützt sein (interne Protokolle). Ein zentrales SSO-System der DPSG steht
derzeit nicht gesichert zur Verfügung.

## Entscheidung
**App-eigene Benutzerverwaltung**: Login per E-Mail + Passwort, Anlage über Admin-Einladung,
Rollen `admin`/`editor`/`reader`. Passwörter mit **Argon2** gehasht, Sessions via JWT.

Die Auth-Schicht wird hinter einer schmalen Schnittstelle gekapselt, sodass ein späterer
Umstieg auf **OIDC/Keycloak** (SSO) ohne Umbau der Fachlogik möglich ist.

## Begründung
- Schnell startklar, keine Abhängigkeit von externer IT-Abstimmung.
- OIDC-Fähigkeit hält die SSO-Option offen.

## Konsequenzen
- **+** Unabhängig, sofort nutzbar.
- **−** Separate Accounts zu pflegen; Passwort-Reset-Flow nötig.
- Rollen-Mapping ist so gewählt, dass es 1:1 auf spätere OIDC-Claims abbildbar ist.
