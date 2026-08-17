from django.db import OperationalError, ProgrammingError

from .models import AppearanceSetting


THEMES = {
    'teal': {
        'label': 'Фирменная бирюза', 'primary': '#41B9B8', 'primary_rgb': '65,185,184',
        'sidebar': '#41B9B8', 'sidebar_glow': '255,255,255', 'sidebar_text': '#FFFFFF', 'sidebar_muted': '#E6FAFA', 'soft': '#E7F8F8', 'soft_hover': '#D1F0F0',
    },
    'indigo': {
        'label': 'Премиальный индиго', 'primary': '#4F46E5', 'primary_rgb': '79,70,229',
        'sidebar': '#111827', 'sidebar_glow': '99,102,241', 'sidebar_text': '#FFFFFF', 'sidebar_muted': '#C7D2FE', 'soft': '#EEF2FF', 'soft_hover': '#E0E7FF',
    },
    'ocean': {
        'label': 'Глубокий океан', 'primary': '#2563EB', 'primary_rgb': '37,99,235',
        'sidebar': '#102A43', 'sidebar_glow': '37,99,235', 'sidebar_text': '#FFFFFF', 'sidebar_muted': '#C9DCF5', 'soft': '#EAF2FF', 'soft_hover': '#D9E8FF',
    },
    'emerald': {
        'label': 'Тёмный изумруд', 'primary': '#059669', 'primary_rgb': '5,150,105',
        'sidebar': '#102A26', 'sidebar_glow': '16,185,129', 'sidebar_text': '#FFFFFF', 'sidebar_muted': '#CBE9DF', 'soft': '#E8F8F2', 'soft_hover': '#D3F0E5',
    },
    'ruby': {
        'label': 'Благородный рубин', 'primary': '#BE3455', 'primary_rgb': '190,52,85',
        'sidebar': '#2B1720', 'sidebar_glow': '190,52,85', 'sidebar_text': '#FFFFFF', 'sidebar_muted': '#F1CBD5', 'soft': '#FCEEF2', 'soft_hover': '#F8DDE5',
    },
    'sky': {
        'label': 'Светлое небо', 'primary': '#3973DC', 'primary_rgb': '57,115,220',
        'sidebar': '#DCEAFF', 'sidebar_glow': '255,255,255', 'sidebar_text': '#17345F', 'sidebar_muted': '#49698F', 'soft': '#EDF4FF', 'soft_hover': '#DCEAFF',
    },
    'sand': {
        'label': 'Тёплый песок', 'primary': '#A66B2B', 'primary_rgb': '166,107,43',
        'sidebar': '#F0E5D2', 'sidebar_glow': '255,255,255', 'sidebar_text': '#3D2C20', 'sidebar_muted': '#755F4D', 'soft': '#F8F1E7', 'soft_hover': '#EEE1CF',
    },
    'violet': {
        'label': 'Яркий фиолетовый', 'primary': '#7C3AED', 'primary_rgb': '124,58,237',
        'sidebar': '#6D28D9', 'sidebar_glow': '196,181,253', 'sidebar_text': '#FFFFFF', 'sidebar_muted': '#E9D5FF', 'soft': '#F3E8FF', 'soft_hover': '#E9D5FF',
    },
    'coral': {
        'label': 'Яркий коралл', 'primary': '#F04F5F', 'primary_rgb': '240,79,95',
        'sidebar': '#E54858', 'sidebar_glow': '255,205,210', 'sidebar_text': '#FFFFFF', 'sidebar_muted': '#FFE4E7', 'soft': '#FFF0F2', 'soft_hover': '#FFDDE2',
    },
}


def crm_theme(request):
    try:
        appearance = AppearanceSetting.objects.filter(pk=1).values('theme', 'color_mode').first() or {}
        selected = appearance.get('theme', AppearanceSetting.Theme.INDIGO)
        color_mode = appearance.get('color_mode', AppearanceSetting.ColorMode.LIGHT)
    except (OperationalError, ProgrammingError):
        selected = AppearanceSetting.Theme.INDIGO
        color_mode = AppearanceSetting.ColorMode.LIGHT
    if selected not in THEMES:
        selected = AppearanceSetting.Theme.INDIGO
    if color_mode not in AppearanceSetting.ColorMode.values:
        color_mode = AppearanceSetting.ColorMode.LIGHT
    return {
        'crm_theme_name': selected, 'crm_theme': THEMES[selected],
        'crm_color_mode': color_mode,
    }
