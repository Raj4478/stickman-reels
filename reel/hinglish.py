"""Devanagari to everyday Roman Hinglish, one word for one word, so the captions show exactly the words being spoken
("एक ही गाँव में" -> "Ek hi gaon mein") and each caption word can light up with its own spoken word.

Common words use the spellings people type on Instagram; other words go through a simple letter-by-letter
transliteration with the silent final "a" dropped (कमल -> kamal, गरीब -> gareeb)."""
import re

COMMON = {
    'है': 'hai', 'हैं': 'hain', 'था': 'tha', 'थी': 'thi', 'थे': 'the', 'में': 'mein', 'मैं': 'main', 'नहीं': 'nahi',
    'और': 'aur', 'यह': 'yeh', 'ये': 'ye', 'वह': 'woh', 'वो': 'woh', 'के': 'ke', 'की': 'ki', 'का': 'ka', 'को': 'ko',
    'से': 'se', 'ने': 'ne', 'पर': 'par', 'तो': 'to', 'भी': 'bhi', 'एक': 'ek', 'हम': 'hum', 'तुम': 'tum', 'आप': 'aap',
    'क्या': 'kya', 'कि': 'ki', 'ही': 'hi', 'हो': 'ho', 'जो': 'jo', 'उस': 'us', 'इस': 'is', 'उसने': 'usne',
    'उसके': 'uske', 'उसकी': 'uski', 'उसका': 'uska', 'उसे': 'use', 'अपने': 'apne', 'अपनी': 'apni', 'अपना': 'apna',
    'मेरा': 'mera', 'मेरी': 'meri', 'मेरे': 'mere', 'मुझे': 'mujhe', 'हमारा': 'hamara', 'हमारी': 'hamari',
    'लेकिन': 'lekin', 'पर': 'par', 'फिर': 'phir', 'तभी': 'tabhi', 'जब': 'jab', 'तब': 'tab', 'सब': 'sab', 'सबसे': 'sabse',
    'बहुत': 'bahut', 'कुछ': 'kuch', 'कोई': 'koi', 'दिन': 'din', 'रात': 'raat', 'घर': 'ghar', 'गाँव': 'gaon', 'गांव': 'gaon',
    'पापा': 'papa', 'माँ': 'maa', 'मां': 'maa', 'बेटी': 'beti', 'बेटा': 'beta', 'पिता': 'pita', 'दादी': 'dadi', 'दादा': 'dada',
    'क्योंकि': 'kyunki', 'याद': 'yaad', 'रखना': 'rakhna', 'प्यार': 'pyaar', 'दिल': 'dil', 'आँखों': 'aankhon',
    'आंखों': 'aankhon', 'आँसू': 'aansu', 'ख़ुशी': 'khushi', 'खुशी': 'khushi', 'शादी': 'shaadi', 'इज़्ज़त': 'izzat',
    'इज्जत': 'izzat', 'दौलत': 'daulat', 'गरीब': 'gareeb', 'ग़रीब': 'gareeb', 'अमीर': 'ameer', 'लोग': 'log', 'साथ': 'saath',
    'कहा': 'kaha', 'बोला': 'bola', 'बोली': 'boli', 'गया': 'gaya', 'गई': 'gayi', 'गए': 'gaye', 'आया': 'aaya', 'आई': 'aayi',
    'आए': 'aaye', 'दिया': 'diya', 'लिया': 'liya', 'किया': 'kiya', 'रहा': 'raha', 'रही': 'rahi', 'रहे': 'rahe',
    'सकता': 'sakta', 'सकती': 'sakti', 'चाहिए': 'chahiye', 'अब': 'ab', 'आज': 'aaj', 'कल': 'kal', 'हमेशा': 'hamesha',
    'स्कूल': 'school', 'पैसे': 'paise', 'पैसा': 'paisa', 'कहानी': 'kahani', 'ज़िंदगी': 'zindagi', 'जिंदगी': 'zindagi',
}
VOWELS = {'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
          'ऑ': 'o'}
MATRAS = {'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ॉ': 'o'}
CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'n', 'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'n', 'ट': 't',
    'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n', 'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n', 'प': 'p', 'फ': 'ph',
    'ब': 'b', 'भ': 'bh', 'म': 'm', 'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'ड़': 'd', 'ढ़': 'dh', 'फ़': 'f', 'य़': 'y',
}
NUKTA = {'क': 'क़', 'ख': 'ख़', 'ग': 'ग़', 'ज': 'ज़', 'ड': 'ड़', 'ढ': 'ढ़', 'फ': 'फ़'}
VIRAMA, NUKTA_SIGN = '्', '़'
NASAL = {'ं': 'n', 'ँ': 'n'}
DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')
PUNCT = {'।': '.', '॥': '.'}


def units(word):
    """The word as [consonant, vowel] units; vowel None after a virama, 'a*' for the inherent vowel."""
    out = []
    chars = list(word)
    i = 0
    while i < len(chars):
        ch = chars[i]
        if i + 1 < len(chars) and chars[i + 1] == NUKTA_SIGN and ch in NUKTA:
            ch = NUKTA[ch]
            i += 1
        nxt = chars[i + 1] if i + 1 < len(chars) else ''
        if ch in CONSONANTS:
            if nxt == VIRAMA:
                out.append([CONSONANTS[ch], None])
                i += 2
                continue
            if nxt in MATRAS:
                out.append([CONSONANTS[ch], MATRAS[nxt]])
                i += 2
                continue
            out.append([CONSONANTS[ch], 'a*'])
        elif ch in VOWELS:
            out.append(['', VOWELS[ch]])
        elif ch in NASAL and out:
            out[-1].append('n')
        elif ch in PUNCT:
            out.append([PUNCT[ch], None])
        elif ch not in (VIRAMA, NUKTA_SIGN, *MATRAS):
            out.append([ch.translate(DIGITS), None])
        i += 1
    return out


def letters(word):
    """Letter by letter, with Hindi's silent schwas dropped: at the end of a word (गरीब -> gareeb) and between a
    vowel and a consonant that has its own vowel (मेहनत -> mehnat, मिलती -> milti)."""
    u = units(word)
    cons = [k for k, x in enumerate(u) if x[0] and x[0] in CONSONANTS.values()]
    if cons and u[cons[-1]][1] == 'a*' and len(u) > 1:
        u[cons[-1]][1] = None  # the final schwa
    for k in range(len(u) - 2, 0, -1):
        if u[k][1] == 'a*' and u[k - 1][1] and u[k + 1][1] and u[k + 1][0]:
            u[k][1] = None
    text = ''.join(c + ((v or '').replace('a*', 'a')) + (x[0] if x else '') for c, v, *x in u)
    # everyday spellings of word endings: रिक्शा -> riksha, मुन्नी -> munni, थीं -> thin
    text = re.sub(r'aa$', 'a', text)
    text = re.sub(r'ee$', 'i', text)
    text = re.sub(r'oo$', 'u', text)
    text = re.sub(r'aan$', 'an', text)
    text = re.sub(r'een$', 'in', text)
    return text


def word(w):
    core = re.sub(r'[।॥,.!?"\'“”‘’-]+$', '', w)
    tail = w[len(core):]
    if not core:
        return ''.join(PUNCT.get(c, c) for c in tail)
    if '-' in core:  # बार-बार -> baar-baar
        return '-'.join(word(part) for part in core.split('-')) + ''.join(PUNCT.get(c, c) for c in tail)
    roman = COMMON.get(core) or letters(core)
    return roman + ''.join(PUNCT.get(c, c) for c in tail)


def hinglish(text):
    """The same words in Roman Hinglish, one for one; the first word capitalised."""
    words = [word(w) for w in str(text or '').split()]
    if words:
        words[0] = words[0][:1].upper() + words[0][1:]
    return ' '.join(words)


def aligned(line, roman):
    """`roman` when it has exactly one word for each Hindi word (the writer's spelling is nicer), else our own."""
    if roman and len(str(roman).split()) == len(str(line).split()):
        return roman
    return hinglish(line)
