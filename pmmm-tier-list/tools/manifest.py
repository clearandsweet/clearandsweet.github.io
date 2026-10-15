# Tier list roster: (slug, kicker, title, source file in src/, crop focus, source credit)
# Focus is the point (0..1) the 2:3 crop is centred on; crops clamp to the image edges.
# A 4-tuple instead is a pixel box (x0, y0, x1, y1) to cut first, e.g. to drop ad copy or a tagline.
# "\n" in a title forces the line break. Order is roughly by release date.
ITEMS = [
    # 2011
    ("madoka-magica-tv", "TV ANIME", "Madoka Magica", "madoka_tv__0.jpg", (0.5, 0.5), "AniList cover (TV key visual)"),
    ("madoka-magica-manga", "MANGA ADAPTATION", "Madoka Magica\n(Manga)", "tv_manga__wiki.jpg", (0.5, 0.5), "Vol. 1 cover (Puella Magi Wiki)"),
    ("kazumi-magica", "MANGA", "Kazumi Magica", "kazumi__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("drama-cd-memories-of-you", "DRAMA CD", "Memories of You", "cd_memories__4.png", (0.30, 0.5), "Magia Exedra event banner for the drama CD"),
    ("oriko-magica", "MANGA", "Oriko Magica", "oriko__0.png", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("drama-cd-sunny-day-life", "DRAMA CD", "Sunny Day Life", "cd_sunny__6.png", (0.30, 0.5), "Magia Exedra event banner for the drama CD"),
    ("madoka-magica-novel", "NOVELIZATION", "Madoka Magica\n(Novel)", "novel__al.jpg", (0.5, 0.5), "Nitroplus Books edition cover (AniList)"),
    ("drama-cd-farewell-story", "DRAMA CD", "Farewell Story", "cd_farewell__10.png", (0.29, 0.5), "Magia Exedra event banner for the drama CD"),
    ("anthology-comics", "ANTHOLOGY", "Anthology\nComics", "anthology__al.png", (0.5, 0.5), "Anthology Comic vol. 1 cover (AniList)"),
    ("madoka-mobage", "GAME", "Madoka Mobage", "game_mobage__0.jpg", (0, 0, 470, 705), "Newtype magazine ad (Puella Magi Wiki)"),
    ("the-beginning-story", "SCENARIO BOOK", "The Beginning\nStory", "beginning_story__cover.jpg", (0.5, 0.5), "Book cover (Puella Magi Wiki)"),
    # 2012
    ("madoka-portable", "GAME", "Madoka Portable", "game_portable__0.jpg", (0.5, 0.25), "PSP key art (Puella Magi Wiki)"),
    ("film-memories", "FILM COMIC", "Film Memories", "film_memories__wiki.jpg", (0.5, 0.5), "Book cover (Puella Magi Wiki)"),
    ("manga-time-kirara-magica", "MAGAZINE + ONE-SHOTS", "Manga Time\nKirara Magica", "kirara_magica__vol1.jpg", (0.5, 0.5), "Issue 1 cover (Puella Magi Wiki)"),
    ("oriko-magica-extra-story", "MANGA", "Oriko Magica:\nExtra Story", "oriko_extra__0.jpg", (0.5, 0.5), "AniList cover"),
    ("drama-cd-summer-training-camp", "DRAMA CD", "Summer Training\nCamp!!", "cd_summer__paola.jpg", (0.5, 0.5), "Paola Bona witch card from the C82 set (Puella Magi Wiki)"),
    ("madoka-online", "GAME", "Madoka Online", "game_online__2.jpeg", (0.5, 0.5), "Official wallpaper (Puella Magi Wiki)"),
    ("beginnings", "RECAP FILM", "Beginnings", "beginnings__al.png", (0.5, 0.5), "Theatrical poster (AniList)"),
    ("eternal", "RECAP FILM", "Eternal", "eternal__al.jpg", (0.5, 0.5), "Theatrical poster (AniList)"),
    ("the-different-story", "MANGA", "The Different Story", "different_story__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("homuras-revenge", "MANGA", "Homura's Revenge!", "homura_revenge__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("homura-tamura", "MANGA", "Homura Tamura", "homura_tamura__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("puella-magi-club", "MANGA", "Puella Magi Club", "magi_club__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("sutema", "MANGA", "Sutema!", "sutema__1.jpg", (0.5, 0.5), "Amazon JP cover (vol. 1)"),
    ("pom-magi", "MANGA", "Pom Magi", "pom_magi__0.jpg", (0.5, 0.5), "Amazon JP cover (vol. 1)"),
    ("madoka-engawa", "MANGA", "Madoka Engawa", "engawa__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("mitakihara-kindergarten", "MANGA", "Mitakihara\nKindergarten", "kindergarten__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("tomoe-mamis-ordinary-days", "MANGA", "Tomoe Mami's\nOrdinary Days", "tomoe_mami__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("mitakihara-anti-materials", "MANGA", "Mitakihara\nAnti-Materials", "anti_materials__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("cafe-grief-seed", "MANGA", "Welcome to\nCafe Grief Seed!", "cafe_grief_seed__0.png", (0.5, 0.5), "AniList cover"),
    ("fuwatto-madoka", "MANGA", "Fuwatto Madoka", "fuwatto__0.jpg", (0.5, 0.5), "Amazon JP cover (vol. 1)"),
    # 2013
    ("rebellion", "FILM", "Rebellion", "rebellion__6.jpg", (0.5, 0.5), "Theatrical poster (Puella Magi Wiki)"),
    ("rebellion-manga", "MANGA ADAPTATION", "Rebellion\n(Manga)", "rebellion_manga__wiki.jpg", (0.5, 0.5), "Vol. 1 cover (Puella Magi Wiki)"),
    ("kanameke", "MANGA", "Kanameke", "kanameke__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("tart-magica", "MANGA", "Tart Magica", "tart__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("oriko-magica-sadness-prayer", "MANGA", "Oriko Magica:\nSadness Prayer", "oriko_sadness__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("suzune-magica", "MANGA", "Suzune Magica", "suzune__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("the-battle-pentagram", "GAME", "The Battle\nPentagram", "game_pentagram__0.jpg", (0.5, 0.5), "Key art (Puella Magi Wiki)"),
    # 2015-2017
    ("wraith-arc", "MANGA", "Wraith Arc", "wraith_arc__0.jpg", (0.5, 0.5), "Amazon JP cover (vol. 1)"),
    ("concept-movie", "SHORT FILM", "Concept Movie", "concept_movie__1.jpg", (0.5, 0.5), "Newtype poster (Puella Magi Wiki)"),
    ("homura-tries-her-best-tomorrow", "MANGA", "Homura Tries Her\nBest Tomorrow!", "homura_ganbaru__0.jpg", (0.5, 0.5), "AniList cover"),
    ("madoka-mobcast", "GAME", "Madoka Mobcast", "game_mobcast__1.jpg", (0.5, 0.5), "Promo art (Puella Magi Wiki)"),
    ("magica-do-bookstore", "MANGA", "Magica-do\nBookstore", "magicado__0.jpg", (0.5, 0.5), "Amazon JP cover"),
    ("magia-report", "MANGA", "Magia Report", "magia_report__0.jpg", (0.5, 0.5), "AniList cover (vol. 1)"),
    ("magia-record-arc-1", "GAME", "Magia Record:\nArc 1", "game_magireco__iroha.png", (0.5, 0.0), "Iroha game art from the official site (Puella Magi Wiki)"),
    # 2018-2021
    ("magia-record-stage-play", "STAGE PLAY", "Magia Record\n(Stage Play)", "stage__2.jpg", (0.43, 0.5), "Stage photo (Puella Magi Wiki)"),
    ("magia-record-manga", "MANGA ADAPTATION", "Magia Record\n(Manga)", "magireco_manga__wiki.png", (0.5, 0.5), "Vol. 1 cover (Puella Magi Wiki)"),
    ("magia-record-another-story", "MANGA ADAPTATION", "Magia Record:\nAnother Story", "another_story__al.jpg", (0.5, 0.5), "Vol. 1 cover (AniList)"),
    ("magia-record-arc-2", "GAME", "Magia Record:\nArc 2", "mr_arc2__iroha_infinite.png", (0.5, 0.0), "Infinite Iroha art (Puella Magi Wiki)"),
    ("magia-record-anime", "TV ANIME", "Magia Record\n(Anime)", "magireco_anime__0.jpg", (0.5, 0.5), "AniList cover"),
    ("null-magical-girl", "NOVEL", "Null Magical Girl", "null_magical_girl__0.jpg", (0.5, 0.5), "10th Anniversary Book cover (Puella Magi Wiki)"),
    # 2023-2026
    ("magia-record-puella-historia", "GAME", "Magia Record:\nPuella Historia", "mr_ph__yachiyo4.jpg", (0.5, 0.35), "Yachiyo (Historia ver.) story art (Puella Magi Wiki)"),
    ("scene0", "GAME STORY", "Madoka Magica:\nscene0", "scene0__0.jpg", (0.5, 0.5), "Key visual (Puella Magi Wiki)"),
    ("magia-et-cetera", "WEB MANGA", "Magia Et Cetera", "etc__vol1.jpeg", (0.5, 0.5), "Vol. 1 cover (Puella Magi Wiki)"),
    ("magia-exedra", "GAME", "Magia Exedra", "game_exedra__3.jpg", (0.5, 0.5), "Official site key visual"),
    ("exedra-quest", "GAME STORY", "Exedra Quest", "eq__name.png", (0.62, 0.5), "Name in the Lighthouse sanctum (Puella Magi Wiki)"),
    ("beginnings-eternal-tv-edition", "TV RECAP", "Beginnings & Eternal\nTV Edition", "tv_edition__wiki.jpg", (0.5, 0.5), "TV Edition poster (Puella Magi Wiki)"),
    ("crescent-memoria", "GAME STORY", "Crescent Memoria", "crescent__kv_sp.jpg", (0.5, 0.5), "Official site key visual"),
    ("yotsugi-peace", "WEB ANIME", "Yotsugi Peace", "yotsugi_peace__0.jpg", (330, 215, 667, 720), "Episode 1 title card (Puella Magi Wiki)"),
    ("walpurgisnacht-rising", "FILM", "Walpurgisnacht:\nRising", "walpurgisnacht__0.jpg", (0.5, 0.5), "AniList cover (theatrical poster)"),
    ("walpurgisnacht-rising-manga", "MANGA ADAPTATION", "Walpurgisnacht:\nRising (Manga)", "wnk_manga__wiki.jpeg", (0.5, 0.5), "Vol. 1 cover (Puella Magi Wiki)"),
    ("sorana-magica", "GAME STORY", "Sorana Magica", "sorana__0.jpeg", (2337, 0, 3882, 2318), "Key visual (Puella Magi Wiki)"),
]

# Gradient (top, bottom) behind cut-out character art; anything not listed uses the default pink.
BACKDROPS = {
    "magia-record-arc-2": ((52, 40, 96), (14, 10, 34)),
}
