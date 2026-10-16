"""Occasions: festivals, special days and seasons, so a Reel about them goes out a few days ahead.

A plain /reel or the daily Reel checks here first. When an occasion is 0-3 days away (and no Reel was made for
it yet this year), the Reel's lesson is that occasion's lesson, and the writer is told to tie the story to it
naturally. Seasons (board exams, results) get one Reel a week while they last. Set the OCCASIONS variable to "off" to skip it.

Festivals are about family, kindness and values here, never religious content. Moving festival dates are
listed per year (checked October 2026: Diwali 8 Nov 2026 / 29 Oct 2027, Holi 22 Mar 2027, Raksha Bandhan
17 Aug 2027, Dussehra 20 Oct 2026 / 9 Oct 2027); add next years' dates to FESTIVALS before they run out.
"""
import datetime as dt
import os

IST = dt.timezone(dt.timedelta(minutes=330))
LEAD_DAYS = 3  # make the Reel up to this many days before the day
SEASON_GAP = 7  # days between two Reels of the same season

# key: (Hindi name, lesson angle for the writer)
OCCASIONS = {
    'new_year': ('नया साल', 'New Year resolutions that actually last: start small and stay consistent'),
    'valentines': ('वैलेंटाइन डे', 'Real love is respect and showing up, not expensive gifts'),
    'womens_day': ('महिला दिवस', 'Respect and support the women at home and at work'),
    'holi': ('होली', 'Holi: let go of old grudges and repair a relationship'),
    'health_day': ('विश्व स्वास्थ्य दिवस', 'Health is the first wealth: one small healthy habit'),
    'mothers_day': ('मदर्स डे', "Mother's Day: a mother's silent sacrifices we notice too late"),
    'fathers_day': ('फादर्स डे', "Father's Day: a father's love shown through hard work, not words"),
    'yoga_day': ('योग दिवस', 'Ten minutes for your body every day changes your whole day'),
    'doctors_day': ('डॉक्टर्स डे', 'Thank the people who quietly take care of us'),
    'friendship_day': ('फ्रेंडशिप डे', 'Friendship Day: a true friend shows up in your worst time'),
    'raksha_bandhan': ('रक्षाबंधन', 'Raksha Bandhan: the promise to stand by your sibling, always'),
    'independence_day': ('स्वतंत्रता दिवस', 'Independence Day: freedom from one bad habit that controls you'),
    'teachers_day': ('शिक्षक दिवस', "Teachers' Day: the teacher who believed in you before you did"),
    'daughters_day': ('डॉटर्स डे', "Daughters' Day: believe in your daughter's dreams"),
    'dussehra': ('दशहरा', 'Dussehra: defeat the "Ravan" inside you: anger, ego, laziness'),
    'diwali': ('दिवाली', 'Diwali: spending to impress others vs saving for your own family'),
    'childrens_day': ('बाल दिवस', "Children's Day: let children be curious and make mistakes"),
    'board_exams': ('बोर्ड परीक्षा', 'Exam season: exam stress, study smart, and marks do not define you'),
    'results': ('रिज़ल्ट', 'Results season: one result does not decide your whole life'),
    'new_session': ('नया सत्र', 'A new school or college year: a fresh start and new habits'),
}

# Festivals that move every year: key -> dates
FESTIVALS = {
    'dussehra': [dt.date(2026, 10, 20), dt.date(2027, 10, 9)],
    'diwali': [dt.date(2026, 11, 8), dt.date(2027, 10, 29)],
    'holi': [dt.date(2027, 3, 22)],
    'raksha_bandhan': [dt.date(2027, 8, 17)],
}
FIXED = {'new_year': (1, 1), 'valentines': (2, 14), 'womens_day': (3, 8), 'health_day': (4, 7), 'yoga_day': (6, 21),
         'doctors_day': (7, 1), 'independence_day': (8, 15), 'teachers_day': (9, 5), 'childrens_day': (11, 14)}
# (month, weekday 0=Monday, which one: 1 = first, -1 = last)
FLOATING = {'mothers_day': (5, 6, 2), 'fathers_day': (6, 6, 3), 'friendship_day': (8, 6, 1), 'daughters_day': (9, 6, 4)}
SEASONS = {'board_exams': ((2, 10), (3, 20)), 'results': ((5, 5), (5, 25)), 'new_session': ((6, 10), (6, 25))}


def nth_weekday(year, month, weekday, n):
    day = dt.date(year, month, 1)
    day += dt.timedelta(days=(weekday - day.weekday()) % 7)
    return day + dt.timedelta(weeks=n - 1)


def dates(year):
    """{key: date} of every one-day occasion in `year`."""
    out = {k: dt.date(year, m, d) for k, (m, d) in FIXED.items()}
    out.update({k: nth_weekday(year, *v) for k, v in FLOATING.items()})
    for key, days in FESTIVALS.items():
        for day in days:
            if day.year == year:
                out[key] = day
    return out


def upcoming(today, days=30):
    """[(date, key)] of one-day occasions in the next `days` days, soonest first."""
    found = []
    for year in (today.year, today.year + 1):
        found += [(d, k) for k, d in dates(year).items() if 0 <= (d - today).days <= days]
    return sorted(found)


def tag(key, day):
    return f'{key}-{day.year}'


def due(today=None, history=()):
    """The occasion to make a Reel about now, or None: {'key', 'tag', 'name', 'lesson', 'date', 'days'}."""
    if os.getenv('OCCASIONS', '').strip().lower() == 'off':
        return None
    today = today or dt.datetime.now(IST).date()
    made = {h.get('occasion') for h in history if h.get('occasion')}
    for day, key in upcoming(today, LEAD_DAYS):
        if tag(key, day) not in made:
            name, lesson = OCCASIONS[key]
            return {'key': key, 'tag': tag(key, day), 'name': name, 'lesson': lesson, 'date': day.isoformat(),
                    'days': (day - today).days}
    for key, (start, end) in SEASONS.items():
        first, last = dt.date(today.year, *start), dt.date(today.year, *end)
        if not first <= today <= last:
            continue
        recent = [h for h in history if (h.get('occasion') or '').startswith(f'{key}-')
                  and h.get('made') and (today - dt.date.fromisoformat(h['made'])).days < SEASON_GAP]
        if not recent:
            name, lesson = OCCASIONS[key]
            return {'key': key, 'tag': f'{key}-{today.year}-{today.isocalendar()[1]}', 'name': name, 'lesson': lesson,
                    'date': today.isoformat(), 'days': 0}
    return None


def upcoming_any(today=None, history=(), days=45):
    """The nearest occasion in the next `days` days not made yet (for the bot's "festival" choice), or None."""
    today = today or dt.datetime.now(IST).date()
    made = {h.get('occasion') for h in history if h.get('occasion')}
    for day, key in upcoming(today, days):
        if tag(key, day) not in made:
            name, lesson = OCCASIONS[key]
            return {'key': key, 'tag': tag(key, day), 'name': name, 'lesson': lesson, 'date': day.isoformat(),
                    'days': (day - today).days}
    return None


def note(occasion):
    """The writer's instruction for an occasion Reel."""
    when = 'today' if occasion['days'] == 0 else f"in {occasion['days']} day{'s' if occasion['days'] > 1 else ''}"
    return (f"- Occasion: {occasion['name']} is {when}. Tie the story to it naturally (the setting, the moment, what "
            'people do that day) and you may mention it in the hook or title, but keep the life lesson the heart of the '
            'Reel. Family, kindness and values only: no religious rituals, gods or religious claims.')


def coming_up(today=None, days=30):
    """A line for the ideas message: what is coming in the next month."""
    today = today or dt.datetime.now(IST).date()
    items = [f"{OCCASIONS[k][0]} ({d.strftime('%d %b')})" for d, k in upcoming(today, days)]
    return ('📅 Coming up: ' + ', '.join(items)) if items else ''
