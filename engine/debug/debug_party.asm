SetDebugNewGameParty: ; unreferenced except in _DEBUG
	ld de, DebugNewGameParty
.loop
	ld a, [de]
	cp -1
	ret z
	ld [wCurPartySpecies], a
	inc de
	ld a, [de]
	ld [wCurEnemyLevel], a
	inc de
	call AddPartyMon
	jr .loop

DebugNewGameParty: ; unreferenced except in _DEBUG
	; Exeggutor is the only debug party member shared with Red, Green, and Japanese Blue.
	; "Tsunekazu Ishihara: Exeggutor is my favorite. That's because I was
	; always using this character while I was debugging the program."
	; From https://web.archive.org/web/20000607152840/http://pocket.ign.com/news/14973.html
	db EXEGGUTOR, 90
IF DEF(_DEBUG)
	db MEW, 5
ELSE
	db MEW, 20
ENDC
	db JOLTEON, 56
	db DUGTRIO, 56
	db ARTICUNO, 57
IF DEF(_DEBUG)
	db PIKACHU, 5
ENDC
	db -1 ; end

PrepareNewGameDebug: ; dummy except in _DEBUG
IF DEF(_DEBUG)
	jp WP004SetParty
ELSE
	ret
ENDC
