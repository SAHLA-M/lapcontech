from django.shortcuts import render
from Product.models import Variants
from django.http import JsonResponse
from django.db.models import Q, Count
from Product.models import Product,Variants
from django.db import models
from admin_panel.models import Product_offer,Brand_offer
import json
from django.views.decorators.cache import never_cache

@never_cache
def home(request):
    variants = Variants.objects.all().order_by('created_at').reverse()[:4]
    recently_viewed = request.session.get('recently_viewed', [])
    recently_viewed_variants= Variants.objects.filter(id__in=recently_viewed)
    exclusive = Product_offer.objects.all().order_by('-percentage').first()
    exclusive_v = None
    if exclusive:
    
         exclusive_v = Variants.objects.filter(product=exclusive.product).first()
    p_offers = Product_offer.objects.all()
    b_offers = Brand_offer.objects.all()
    offerd_product_ides = [p_offer.product.id for p_offer in p_offers]
    offerd_brand_ides = [b_offer.brand.id for b_offer in b_offers]
    return render(request, 'index.html',{
        'variants':variants,
        'recently_viewed_variants':recently_viewed_variants,
        'p_offers':p_offers,
        'b_offers':b_offers,
        'offerd_product_ides': offerd_product_ides,
        'offerd_brand_ides': offerd_brand_ides,
        'exclusive':exclusive,
        'exclusive_v':exclusive_v,
        })


