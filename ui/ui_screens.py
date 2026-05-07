"""
ui/ui_screens.py

Ecrans en overlay : pause, game over, choix de level-up.
Extrait de ui.py pour garder ce fichier lisible.
"""

import random
import pygame
from core.config import ALL_TOWER_TYPES, GRID_WIDTH, GRID_HEIGHT

# Ces constantes sont definies ici plutot qu'importees depuis ui.ui
# pour eviter l'import circulaire ui.py <-> ui_screens.py
def get_font(size_key="md", bold=False):
    sizes = {"xs": 14, "sm": 18, "md": 22, "lg": 30, "xl": 48}
    return pygame.font.SysFont("arial", sizes.get(size_key, 22), bold=bold)

COLORS = {
    "bg":         (15,  18,  28),
    "panel":      (29,  35,  51),
    "panel_alt":  (36,  44,  64),
    "border":     (88,  103, 138),
    "text":       (236, 240, 250),
    "muted":      (163, 173, 196),
    "accent":     (255, 205, 92),
    "accent_alt": (111, 205, 255),
    "success":    (96,  224, 138),
    "danger":     (240, 99,  99),
}

ITEM_LABELS = {
    "small":          "Tour Rapide",
    "big":            "Tour Lourde",
    "sniper":         "Sniper",
    "mortar":         "Mortier",
    "frost":          "Geleuse",
    "poison":         "Venimeuse",
    "beam":           "Laser",
    "tesla":          "Tesla",
    "rocket":         "Roquette",
    "storm":          "Tempete",
    "arcane":         "Arcane",
    "crystal":        "Cristal",
    "swarm":          "Essaim",
    "burst":          "Fusee",
    "cannon":         "Canon",
    "flamethrower":   "Flammes",
    "shock":          "Eclair",
    "mine":           "Mine",
    "laser":          "Laser",
    "trap":           "Piege",
    "tower_damage":   "Boost Degats",
    "tower_cooldown": "Boost Vitesse",
}

ITEM_COLORS = {
    "small":          (0,   150, 200),
    "big":            (0,   100, 180),
    "sniper":         (230, 180, 60),
    "mortar":         (180, 90,  50),
    "frost":          (120, 200, 255),
    "poison":         (80,  180, 80),
    "beam":           (180, 60,  220),
    "tesla":          (120, 180, 250),
    "rocket":         (200, 100, 40),
    "storm":          (90,  130, 240),
    "arcane":         (150, 60,  220),
    "crystal":        (80,  220, 220),
    "swarm":          (220, 140, 50),
    "burst":          (200, 70,  70),
    "cannon":         (140, 90,  30),
    "flamethrower":   (220, 120, 40),
    "shock":          (255, 180, 60),
    "mine":           (120, 80,  50),
    "laser":          (180, 60,  180),
    "trap":           (100, 100, 100),
    "tower_damage":   (240, 120, 40),
    "tower_cooldown": (90,  200, 180),
}

TOWER_DESCS = {
    "small":          "Tour rapide\nDegats corrects\nPortee courte",
    "big":            "Tour lourde\nDegats puissants\nPortee moyenne",
    "sniper":         "Tir longue portee\nCritique precis\nDommages eleves",
    "mortar":         "Mortier\nImpact AoE\nPlacement strategique",
    "frost":          "Geleuse\nRalentit les ennemis\nControle de zone",
    "poison":         "Venimeuse\nDegats sur le temps\nAffaiblit la cible",
    "beam":           "Laser continu\nDegats rapides\nPenetration",
    "tesla":          "Tesla\nChocs electriques\nChaines ennemis",
    "rocket":         "Roquette\nExplosion AoE\nPortee moyenne",
    "storm":          "Tempete\nFoudre aleatoire\nZone etendue",
    "arcane":         "Arcane\nMagie pure\nDommages bruts",
    "crystal":        "Cristal\nZone gelee\nRenforce le champ",
    "swarm":          "Essaim\nTir rapide\nFaible degats",
    "burst":          "Fusee\nSalve lourde\nCooldown long",
    "cannon":         "Canon\nDegats lourds\nImpact de zone",
    "flamethrower":   "Flammes\nZone de feu\nDegats continus",
    "shock":          "Eclair\nDegats electriques\nLenteur ciblee",
    "mine":           "Mine\nDetonation surprise\nDegats massifs",
    "laser":          "Laser\nPortee maximale\nTir precis",
    "trap":           "Piege\nDegats au contact\nDefense statique",
    "tower_damage":   "Augmente les degats\nDe toutes les tours\nIdeal pour burst",
    "tower_cooldown": "Reduit le cooldown\nDes tours\nForte cadence de tir",
}


# ECRAN DE PAUSE

# Etat global de la popup de confirmation — None si pas de popup ouverte
_pause_confirm_pending = None
_popup_opened          = False


def draw_pause_screen(screen, big_font, font, mouse_pos=(0, 0), clicked=False):
    """
    Overlay de pause avec 3 boutons : Continuer / Recommencer / Menu.
    Recommencer et Menu ouvrent une popup de confirmation avant d'agir.
    Retourne "resume", "restart", "menu" ou None.
    """
    global _pause_confirm_pending, _popup_opened

    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    pt = big_font.render("PAUSE", True, COLORS["accent"])
    screen.blit(pt, ((w - pt.get_width()) // 2, h // 2 - 130))

    mx, my   = mouse_pos
    btn_w    = 240
    btn_h    = 54
    gap      = 16
    total_h  = 3 * btn_h + 2 * gap
    start_y  = h // 2 - total_h // 2 + 20

    buttons = [
        ("Continuer",   "resume",  (60, 160, 80),  (150, 255, 160)),
        ("Recommencer", "restart", (60, 80,  160), (150, 160, 255)),
        ("Menu",        "menu",    (120, 50, 50),  (255, 130, 130)),
    ]

    action       = None
    confirm_open = _pause_confirm_pending is not None

    for i, (label, key, col_n, col_h) in enumerate(buttons):
        bx   = (w - btn_w) // 2
        by   = start_y + i * (btn_h + gap)
        rect = pygame.Rect(bx, by, btn_w, btn_h)
        # Boutons non-cliquables quand la popup de confirmation est ouverte
        hov  = rect.collidepoint(mx, my) and not confirm_open
        pygame.draw.rect(screen, col_h if hov else col_n, rect, border_radius=12)
        pygame.draw.rect(screen, (255, 255, 255) if hov else (180, 180, 200), rect, 2, border_radius=12)
        lbl = font.render(label, True, (255, 255, 255))
        screen.blit(lbl, (bx + (btn_w - lbl.get_width()) // 2,
                           by + (btn_h - lbl.get_height()) // 2))
        if clicked and hov:
            if key == "resume":
                action = key
            else:
                # Recommencer/Menu demandent confirmation — on stocke l'action en attente
                _pause_confirm_pending = key
                _popup_opened = True

    if _pause_confirm_pending is not None:
        # On passe clicked=False le premier frame pour eviter de confirmer instantanement
        result = _draw_confirm_popup(
            screen, font, big_font, mouse_pos,
            False if _popup_opened else clicked,
            _pause_confirm_pending
        )
        _popup_opened = False
        if result == "ok":
            action = _pause_confirm_pending
            _pause_confirm_pending = None
        elif result == "cancel":
            _pause_confirm_pending = None

    return action


def _draw_confirm_popup(screen, font, big_font, mouse_pos, clicked, pending_key):
    """
    Popup modale de confirmation avant de quitter ou recommencer.
    Le premier frame apres ouverture ignore le clic pour eviter une confirmation accidentelle.
    Retourne "ok", "cancel" ou None.
    """
    w, h = screen.get_size()
    veil = pygame.Surface((w, h), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 180))
    screen.blit(veil, (0, 0))

    title_txt = "Recommencer la partie ?" if pending_key == "restart" else "Retour au menu ?"
    sub_txt   = "La progression de cette partie sera perdue."
    t  = big_font.render(title_txt, True, (255, 230, 150))
    st = font.render(sub_txt, True, (220, 200, 150))

    bw, bh   = 170, 46
    gap      = 20
    pad_x    = 36
    pad_y    = 22
    btn_total_w = bw * 2 + gap
    pop_w    = max(t.get_width(), st.get_width(), btn_total_w) + pad_x * 2
    pop_h    = pad_y + t.get_height() + 12 + st.get_height() + 22 + bh + pad_y
    pop      = pygame.Rect((w - pop_w) // 2, (h - pop_h) // 2, pop_w, pop_h)

    pygame.draw.rect(screen, (28, 22, 14), pop, border_radius=12)
    pygame.draw.rect(screen, (200, 170, 60), pop, 2, border_radius=12)

    screen.blit(t,  (pop.centerx - t.get_width()  // 2, pop.y + pad_y))
    screen.blit(st, (pop.centerx - st.get_width() // 2, pop.y + pad_y + t.get_height() + 12))

    mx, my      = mouse_pos
    by          = pop.bottom - bh - pad_y
    bx_ok       = pop.centerx - btn_total_w // 2
    bx_cancel   = bx_ok + bw + gap
    ok_rect     = pygame.Rect(bx_ok,     by, bw, bh)
    cancel_rect = pygame.Rect(bx_cancel, by, bw, bh)
    ok_hov      = ok_rect.collidepoint(mx, my)
    can_hov     = cancel_rect.collidepoint(mx, my)

    pygame.draw.rect(screen, (160, 60, 60) if ok_hov else (110, 40, 40), ok_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 180, 180), ok_rect, 2, border_radius=10)
    ok_lbl = font.render("Confirmer", True, (255, 255, 255))
    screen.blit(ok_lbl, (ok_rect.centerx - ok_lbl.get_width() // 2,
                          ok_rect.centery - ok_lbl.get_height() // 2))

    pygame.draw.rect(screen, (60, 100, 60) if can_hov else (40, 70, 40), cancel_rect, border_radius=10)
    pygame.draw.rect(screen, (180, 230, 180), cancel_rect, 2, border_radius=10)
    can_lbl = font.render("Annuler", True, (255, 255, 255))
    screen.blit(can_lbl, (cancel_rect.centerx - can_lbl.get_width() // 2,
                           cancel_rect.centery - can_lbl.get_height() // 2))

    if clicked:
        if ok_hov:
            return "ok"
        if can_hov:
            return "cancel"
    return None


# ECRAN GAME OVER / VICTOIRE

def draw_gameover_screen(screen, big_font, font, win, mouse_pos, clicked, reward_coins=0):
    """
    Ecran de fin de partie mode normal — victoire verte, defaite rouge.
    Deux boutons : Rejouer et Menu Principal.
    Retourne "restart", "menu" ou None.
    """
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    msg, color = ("VICTOIRE !", (80, 255, 80)) if win else ("DEFAITE", (255, 60, 60))
    title = big_font.render(msg, True, color)
    screen.blit(title, ((w - title.get_width()) // 2, h // 2 - 100))

    if win:
        subtitle = font.render(f"+{reward_coins} pieces gagnees", True, (240, 220, 140))
    else:
        subtitle = font.render("Essayez encore !", True, (240, 220, 140))
    screen.blit(subtitle, ((w - subtitle.get_width()) // 2, h // 2 - 40))

    btn_w = 220
    btn_h = 52
    mx, my = mouse_pos

    # Bouton Rejouer
    btn_rect = pygame.Rect((w - btn_w) // 2, h // 2 + 20, btn_w, btn_h)
    hov      = btn_rect.collidepoint(mx, my)
    pygame.draw.rect(screen, (100, 180, 100) if hov else (60, 120, 60), btn_rect, border_radius=10)
    pygame.draw.rect(screen, (200, 255, 200), btn_rect, 2, border_radius=10)
    lbl = font.render("Rejouer", True, (255, 255, 255))
    screen.blit(lbl, (btn_rect.x + (btn_w - lbl.get_width()) // 2,
                       btn_rect.y + (btn_h - lbl.get_height()) // 2))

    # Bouton Menu Principal
    menu_btn = pygame.Rect((w - btn_w) // 2, h // 2 + 90, btn_w, btn_h)
    mhov     = menu_btn.collidepoint(mx, my)
    pygame.draw.rect(screen, (60, 80, 160) if mhov else (40, 55, 110), menu_btn, border_radius=10)
    pygame.draw.rect(screen, (150, 180, 255), menu_btn, 2, border_radius=10)
    mlbl = font.render("Menu Principal", True, (255, 255, 255))
    screen.blit(mlbl, (menu_btn.x + (menu_btn.w - mlbl.get_width()) // 2,
                        menu_btn.y + (menu_btn.h - mlbl.get_height()) // 2))

    if clicked:
        if hov:
            return "restart"
        if mhov:
            return "menu"
    return None


# MESSAGE DE DEMARRAGE

def draw_start_hint(screen, font, offset_x, offset_y):
    """Texte centre sur la grille avant que le joueur place sa premiere tour."""
    hint = font.render("Placez une tour pour demarrer", True, (220, 220, 100))
    screen.blit(hint, (
        offset_x + (GRID_WIDTH  - hint.get_width())  // 2,
        offset_y + (GRID_HEIGHT - hint.get_height()) // 2,
    ))


# LEVEL-UP BANNER

def pick_three_towers():
    """Retourne 3 types de tours uniques — avec fallback si le pool est trop petit."""
    pool = list(ALL_TOWER_TYPES) * 2
    random.shuffle(pool)
    seen = []
    for t in pool:
        if t not in seen:
            seen.append(t)
        if len(seen) == 3:
            break
    # Securite si moins de 3 types dans le pool — tres peu probable mais on evite le crash
    while len(seen) < 3:
        seen.append(random.choice(ALL_TOWER_TYPES))
    return seen[:3]


def draw_levelup_banner(screen, big_font, font, choices, mouse_pos, clicked):
    """
    Banniere de level-up avec 3 cartes de tours a choisir.
    Overlay gris fonce pour que les cartes ressortent bien.
    Retourne le type de tour choisi (str) ou None si pas encore clique.
    """
    w, h = screen.get_size()

    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((20, 20, 30, 190))
    screen.blit(overlay, (0, 0))

    title_surf = big_font.render("CHOIX DE TOUR", True, (255, 220, 60))
    screen.blit(title_surf, (w // 2 - title_surf.get_width() // 2, h // 5 - 20))

    sub = font.render("Choisissez la tour a ajouter a votre inventaire", True, (200, 200, 200))
    screen.blit(sub, (w // 2 - sub.get_width() // 2, h // 5 + 32))

    card_w  = 160
    card_h  = 200
    gap     = 30
    total_w = 3 * card_w + 2 * gap
    start_x = (w - total_w) // 2
    card_y  = h // 2 - card_h // 2
    chosen  = None
    mx, my  = mouse_pos

    for i, tower_type in enumerate(choices):
        cx   = start_x + i * (card_w + gap)
        rect = pygame.Rect(cx, card_y, card_w, card_h)
        hov  = rect.collidepoint(mx, my)

        base = ITEM_COLORS.get(tower_type, (80, 80, 80))
        col  = tuple(min(255, c + 40) for c in base) if hov else base
        pygame.draw.rect(screen, col, rect, border_radius=14)
        bdr  = (255, 220, 60) if hov else (150, 150, 180)
        pygame.draw.rect(screen, bdr, rect, 3 if hov else 1, border_radius=14)

        # Icone circulaire avec la premiere lettre de la tour
        icon_r = 36
        pygame.draw.circle(screen, (255, 255, 255), (cx + card_w // 2, card_y + 60), icon_r)
        pygame.draw.circle(screen, bdr,             (cx + card_w // 2, card_y + 60), icon_r, 2)
        ilbl = big_font.render(tower_type[0].upper(), True, col)
        screen.blit(ilbl, (cx + card_w // 2 - ilbl.get_width() // 2,
                            card_y + 60 - ilbl.get_height() // 2))

        # Nom de la tour
        nlbl = font.render(ITEM_LABELS.get(tower_type, tower_type), True, (255, 255, 255))
        screen.blit(nlbl, (cx + (card_w - nlbl.get_width()) // 2, card_y + 108))

        # Description sur plusieurs lignes si necessaire
        desc_font  = get_font("sm")
        desc_lines = TOWER_DESCS.get(tower_type, "").split("\n")
        for li, line in enumerate(desc_lines):
            dl = desc_font.render(line, True, (200, 220, 255))
            screen.blit(dl, (cx + (card_w - dl.get_width()) // 2,
                              card_y + 136 + li * 18))

        if clicked and hov:
            chosen = tower_type

    return chosen