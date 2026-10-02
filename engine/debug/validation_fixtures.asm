; WP004 controlled starting states; no RNG override or battle-rule changes.
ASSERT DEF(_DEBUG)

WP004BattleFixture::
	xor a
	ld [wStatusFlags6], a
	ld [wLinkState], a
	ld [wOptionsInitialized], a
	ld [wIsInBattle], a
	ld [wBattleType], a
	call PrepareOakSpeech ; clears player/main/party/box and sprite data
	predef InitPlayerData2 ; empty terminated bags; default objects and money
	call WP004SetParty
	call ClearScreen
	call LoadFontTilePatterns
	call LoadHpBarAndStatusTilePatterns
	call GBPalNormal
	; Ordinary trainer battle: Youngster #2, one level 14 Spearow.
	; BIT_TEST_BATTLE stays clear: normal move selection and battle rules.
	ld a, OPP_YOUNGSTER
	ld [wCurOpponent], a
	ld a, 2
	ld [wTrainerNo], a
WP004BattleReady::
	predef InitOpponent
	ld a, 1
	ld [wUpdateSpritesEnabled], a
	ldh [hAutoBGTransferEnabled], a
	jp WP004BattleFixture ; rebuild the state after victory or defeat

WP004MapFixture::
	xor a
	ld [wDefaultMap], a ; PALLET_TOWN
	ld [wLinkState], a
	ld [wOptionsInitialized], a
	ld a, 1 << BIT_DEBUG_MODE
	ld [wStatusFlags6], a ; do not inherit bicycle or warp flags
	call OakSpeech ; clears state, initializes defaults, uses Pallet fly warp
	ld hl, wStatusFlags6
	res BIT_DEBUG_MODE, [hl] ; ordinary movement/encounters after setup
	; Deliberately minimal synthetic progression, not a full post-intro save.
	SetEvent EVENT_FOLLOWED_OAK_INTO_LAB
	SetEvent EVENT_GOT_STARTER
WP004MapReady::
	jp SpecialEnterMap

WP004SetParty::
	; Fixed ID matches party OT; zero badges, no stat boosts or traded obedience.
	ld a, $12
	ld [wPlayerID], a
	ld a, $34
	ld [wPlayerID + 1], a
	ld hl, wPartyCount
	ld a, 1
	ld [hli], a
	ld a, RHYDON
	ld [hli], a
	ld [hl], $ff
	ld hl, WP004PartyMon
	ld de, wPartyMon1
	ld bc, PARTYMON_STRUCT_LENGTH
	call CopyData
	ld hl, WP004Nickname
	ld de, wPartyMon1Nick
	ld bc, NAME_LENGTH
	call CopyData
	ld hl, wPlayerName
	ld de, wPartyMon1OT
	ld bc, NAME_LENGTH
	jp CopyData

WP004PartyMon:
	db RHYDON
	db HIGH(72), LOW(72) ; current HP, big endian
	db 20, 0, GROUND, ROCK, 60 ; box level, status, types, catch rate
	db HORN_ATTACK, STOMP, TAIL_WHIP, FURY_ATTACK
	db $12, $34 ; OT ID
	db 0, HIGH(10000), LOW(10000) ; level 20, slow growth
	ds NUM_STATS * 2, 0 ; no stat experience
	db $88, $88 ; fixed DVs; derived HP DV is zero
	db 25, 20, 30, 20 ; full PP, no PP Ups
	db 20
	db 0, 72, 0, 60, 0, 56, 0, 24, 0, 26 ; HP/Atk/Def/Speed/Special
	ASSERT @ - WP004PartyMon == PARTYMON_STRUCT_LENGTH
WP004Nickname:
	db "RHYDON@@@@@"
	ASSERT @ - WP004Nickname == NAME_LENGTH
