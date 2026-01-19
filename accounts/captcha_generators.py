# # accounts/captcha_generators.py
# import random
# from django.conf import settings
# from django.core.cache import cache
# from django.urls import reverse

# def random_numeric_challenge():
#     """
#     Generates a 5-digit numeric CAPTCHA like '03842'.
#     """
#     digits = ''.join([str(random.randint(0, 9)) for _ in range(5)])
#     return digits, digits

import random

def random_numeric_challenge():
    """
    Generates a 5-digit numeric CAPTCHA like '03842'.
    """
    digits = ''.join([str(random.randint(0, 9)) for _ in range(5)])
    return digits, digits
