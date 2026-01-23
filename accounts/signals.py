

from django.db.models.signals import post_save, m2m_changed, pre_save
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal
from datetime import date
from .models import (
    Property, 
    PropertyContribution, 
    PropertyProfitDistribution,
    User,
    Expense,
    OfficeCost
)
from .utils import create_story, format_currency
from threading import local


_thread_locals = local()


@receiver(post_save, sender=Property)
def property_create_story(sender, instance, created, **kwargs):
    """Create story when property is created"""
    if created and instance.status in ['wishlist', 'bought']:
        msg = f"The house current status is '{instance.get_status_display()}'"
        create_story(msg, instance.updated_at, instance)


@receiver(pre_save, sender=Property)
def property_change_story(sender, instance, **kwargs):
    """Create story when property is updated"""
    if not instance.pk:
        return

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    
    if not old.buying_date and instance.buying_date:
        msg = f"House '{instance.title}' was bought for ${format_currency(instance.auction_price)}"
        create_story(msg, instance.updated_at, instance)

    if not old.selling_date and instance.selling_date:
        msg = f"House '{instance.title}' was sold for ${format_currency(instance.selling_price)}"
        create_story(msg, instance.updated_at, instance)

    if old.selling_price != instance.selling_price and instance.selling_price:
        msg = f"Selling price updated from ${format_currency(old.selling_price)} to ${format_currency(instance.selling_price)}"
        create_story(msg, instance.updated_at, instance)

    if old.asking_price != instance.asking_price and instance.asking_price:
        msg = f"Asking price updated from ${format_currency(old.asking_price)} to ${format_currency(instance.asking_price)}"
        create_story(msg, instance.updated_at, instance)

    if old.auction_price != instance.auction_price:
        msg = f"Auction price updated from ${format_currency(old.auction_price)} to ${format_currency(instance.auction_price)}"
        create_story(msg, instance.updated_at, instance)
    
    if old.buying_price != instance.buying_price:
        msg = f"Buying price updated from ${format_currency(old.buying_price)} to ${format_currency(instance.buying_price)}"
        create_story(msg, instance.updated_at, instance)

    if old.service_cost != instance.service_cost:
        msg = f"Service Cost updated from ${format_currency(old.service_cost)} to ${format_currency(instance.service_cost)}"
        create_story(msg, instance.updated_at, instance)

    if old.status != instance.status:
        msg = f"The house current status is '{instance.get_status_display()}'"
        create_story(msg, instance.updated_at, instance)




@receiver(pre_save, sender=Expense)
def cache_old_expense_status(sender, instance, **kwargs):
    """Cache old expense status before saving"""
    if not instance.pk:
        _thread_locals.old_expense_status = None
    else:
        old_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        _thread_locals.old_expense_status = old_status


@receiver(post_save, sender=Expense)
def create_story_after_expense_approval(sender, instance, created, **kwargs):
    """Create story when expense is approved"""
    if created:
        return

    old_status = getattr(_thread_locals, 'old_expense_status', None)
    new_status = instance.status
    
    if old_status != 'approved' and new_status == 'approved':
        prop = instance.property
        if prop:
            message = f"Expense approved: {instance.purpose} – {format_currency(instance.amount)} USD"
            create_story(message, instance.updated_at, prop)


@receiver(pre_save, sender=Property)
def track_property_changes(sender, instance, **kwargs):
    """
    Track property changes before saving
    
    ✅ NEW: Set _is_being_created flag for new properties
    """
    if instance.pk:
        try:
            previous = Property.objects.get(pk=instance.pk)
            instance._previous_buying_price = previous.buying_price
            instance._previous_service_cost = previous.service_cost
            instance._previous_status = previous.status
            instance._previous_contributors = set(previous.contributors.all())
            instance._is_being_created = False  # Existing property
        except Property.DoesNotExist:
            pass
    else:
        # New property being created
        instance._previous_buying_price = None
        instance._previous_service_cost = None
        instance._previous_status = None
        instance._previous_contributors = set()
        instance._is_being_created = True  # ✅ Flag for creation


@receiver(post_save, sender=Property)
def create_profit_distribution_on_property_create(sender, instance, created, **kwargs):

    if created:
        profit_dist, dist_created = PropertyProfitDistribution.objects.get_or_create(
            property=instance,
            defaults={
                'first_level_share': Decimal('1.00'),
                'second_level_share': Decimal('1.00'),
            }
        )

        if dist_created:
            print(f"\n{'='*70}")
            print("✅ PropertyProfitDistribution CREATED")
            print(f"   Property: {instance.property_name}")
            print(f"   First Level Share: {profit_dist.first_level_share}")
            print(f"   Second Level Share: {profit_dist.second_level_share}")
            print(f"{'='*70}\n")


# @receiver(post_save, sender=Property)
# def create_profit_distribution_on_property_create(sender, instance, created, **kwargs):

#     if created:
#         profit_dist, created = PropertyProfitDistribution.objects.get_or_create(
#             property=instance,
#             defaults={
#                 'first_level_share': Decimal('1.00'),
#                 'second_level_share': Decimal('1.00'),
#             }
#         )
        
#         if created:
#             print(f"\n{'='*70}")
#             print(f"✅ PropertyProfitDistribution CREATED")
#             print(f"   Property: {instance.title}")
#             print(f"   First Level Share: {profit_dist.first_level_share}")
#             print(f"   Second Level Share: {profit_dist.second_level_share}")
#             print(f"{'='*70}\n")


@receiver(m2m_changed, sender=Property.contributors.through)
def handle_contributors_m2m_change(sender, instance, action, pk_set, **kwargs):

    
    if action not in ['post_add', 'post_remove']:
        return
    
    if not pk_set:
        return
    
    try:
        profit_dist, _ = PropertyProfitDistribution.objects.get_or_create(
            property=instance,
            defaults={
                'first_level_share': Decimal('1.00'),
                'second_level_share': Decimal('1.00'),
            }
        )
    except Exception as e:
        print(f"❌ Error getting PropertyProfitDistribution: {e}")
        return
    
   
    if action == 'post_add':
        with transaction.atomic():
            
            is_first_contributor_addition = profit_dist.first_level_buyers.count() == 0
            
            print(f"\n{'='*70}")
            print(f"🆕 ADDING CONTRIBUTORS")
            print(f"   Property: {instance.title}")
            print(f"   Is First Contributor Addition: {is_first_contributor_addition}")
            print(f"   Current First Level Count: {profit_dist.first_level_buyers.count()}")
            print(f"   Users to Add: {len(pk_set)}")
            print(f"{'='*70}")
            
            for user_id in pk_set:
                try:
                    user = User.objects.get(id=user_id)
                    
                   
                    already_first_level = profit_dist.first_level_buyers.filter(id=user_id).exists()
                    already_second_level = profit_dist.second_level_buyers.filter(id=user_id).exists()
                    
                    if is_first_contributor_addition:
                        
                        if not already_first_level:
                            profit_dist.first_level_buyers.add(user)
                            print(f"   ✅ {user.get_full_name()} → FIRST LEVEL (Initial Creation)")
                        else:
                            print(f"   ℹ️  {user.get_full_name()} → Already in FIRST LEVEL")
                    
                    else:
                       
                        if not already_second_level:
                            profit_dist.second_level_buyers.add(user)
                            print(f"   ✅ {user.get_full_name()} → SECOND LEVEL (Added Later)")
                        else:
                            print(f"   ℹ️  {user.get_full_name()} → Already in SECOND LEVEL")
                
                except User.DoesNotExist:
                    print(f"   ❌ User ID {user_id} not found")
                    continue
            
            
            profit_dist.update_buyer_counts()
            
            print(f"\n📊 UPDATED COUNTS:")
            print(f"   First Level: {profit_dist.first_level_buyer_count}")
            print(f"   Second Level: {profit_dist.second_level_buyer_count}")
            print(f"{'='*70}\n")
    
    
    elif action == 'post_remove':
        with transaction.atomic():
            print(f"\n{'='*70}")
            print(f"🗑️  REMOVING CONTRIBUTORS")
            print(f"   Property: {instance.title}")
            print(f"   Users to Remove: {len(pk_set)}")
            print(f"{'='*70}")
            
            for user_id in pk_set:
                removed_from_first = False
                removed_from_second = False
                
                
                if profit_dist.first_level_buyers.filter(id=user_id).exists():
                    profit_dist.first_level_buyers.remove(user_id)
                    removed_from_first = True
                
                
                if profit_dist.second_level_buyers.filter(id=user_id).exists():
                    profit_dist.second_level_buyers.remove(user_id)
                    removed_from_second = True
                
                if removed_from_first or removed_from_second:
                    levels = []
                    if removed_from_first:
                        levels.append("FIRST")
                    if removed_from_second:
                        levels.append("SECOND")
                    print(f"   ✅ Removed User ID {user_id} from {' & '.join(levels)} LEVEL")
            
            
            profit_dist.update_buyer_counts()
            
            print(f"\n📊 UPDATED COUNTS:")
            print(f"   First Level: {profit_dist.first_level_buyer_count}")
            print(f"   Second Level: {profit_dist.second_level_buyer_count}")
            print(f"{'='*70}\n")


@receiver(post_save, sender=PropertyContribution)
def track_contribution_sequences(sender, instance, created, **kwargs):

    
    if not created:
        return
    
   
    if instance.investment_sequence <= 1:
        return
    
    try:
        profit_dist, _ = PropertyProfitDistribution.objects.get_or_create(
            property=instance.property,
            defaults={
                'first_level_share': Decimal('1.00'),
                'second_level_share': Decimal('1.00'),
            }
        )
        
        user = instance.user
        
        
        if profit_dist.second_level_buyers.filter(id=user.id).exists():
            return
        
        with transaction.atomic():
            
            profit_dist.second_level_buyers.add(user)
            profit_dist.update_buyer_counts()
            
            print(f"\n{'='*70}")
            print(f"🔵 SECOND LEVEL TRACKING")
            print(f"   Property: {instance.property.title}")
            print(f"   User: {user.get_full_name()}")
            print(f"   Investment Sequence: #{instance.investment_sequence}")
            print(f"   ✅ Added to SECOND LEVEL (Repeat Investment)")
            print(f"\n📊 UPDATED COUNTS:")
            print(f"   First Level: {profit_dist.first_level_buyer_count}")
            print(f"   Second Level: {profit_dist.second_level_buyer_count}")
            print(f"{'='*70}\n")
    
    except Exception as e:
        print(f"❌ Error in track_contribution_sequences: {e}")


# from django.db.models.signals import post_save, pre_save
# from django.dispatch import receiver
# from .models import Property, Expense
# from .utils import create_story, format_currency
# from threading import local
# _thread_locals = local()

# # ================================
# # 1. Property Change Signal
# # ================================
# @receiver(post_save, sender=Property)
# def property_create_story(sender, instance, created, **kwargs):
#     if created and instance.status == 'wishlist':
#         msg = f"The house current status is '{instance.get_status_display()}'"
#         create_story(msg, instance.updated_at, instance)
        
#     if created and instance.status == 'bought':
#         msg = f"The house current status is '{instance.get_status_display()}'"
#         create_story(msg, instance.updated_at, instance)
        
# @receiver(pre_save, sender=Property)
# def property_change_story(sender, instance, **kwargs):
#     if not instance.pk:
#         return

#     old = sender.objects.get(pk=instance.pk)
    
#     # Example: Bought
#     if not old.buying_date and instance.buying_date:
#         msg = f"House ‘{instance.title}’ was bought for ${format_currency(instance.auction_price)}"
#         create_story(msg, instance.updated_at, instance)

#     # Example: Sold
#     if not old.selling_date and instance.selling_date:
#         msg = f"House ‘{instance.title}’ was sold for ${format_currency(instance.selling_price)}"
#         create_story(msg, instance.updated_at, instance)

#     # Example: Selling price update
#     if old.selling_price != instance.selling_price and instance.selling_price:
#         msg = f"Selling price updated from ${format_currency(old.selling_price)} to ${format_currency(instance.selling_price)} ’"
#         create_story(msg, instance.updated_at, instance)

#     # Example: Asking price update
#     if old.asking_price != instance.asking_price and instance.asking_price:
#         msg = f"Asking price updated from ${format_currency(old.asking_price)} to ${format_currency(instance.asking_price)}’"
#         create_story(msg, instance.updated_at, instance)

#     # Example: Auction price update
#     if old.auction_price != instance.auction_price:
#         msg = f"Auction price updated from ${format_currency(old.auction_price)} to ${format_currency(instance.auction_price)}’"
#         create_story(msg, instance.updated_at, instance)
    
#     # Example: Auction price update
#     if old.buying_price != instance.buying_price:
#         msg = f"Auction price updated from ${format_currency(old.buying_price)} to ${format_currency(instance.buying_price)}’"
#         create_story(msg, instance.updated_at, instance)

#     # Example: service cost price update
#     if old.service_cost != instance.service_cost:
#         msg = f"Sercice Cost updated from ${format_currency(old.service_cost)} to ${format_currency(instance.service_cost)}’"
#         create_story(msg, instance.updated_at, instance)

#     # Example: status update
#     if old.status != instance.status:
#         msg = f"The house current status is '{instance.get_status_display()}'"
#         create_story(msg, instance.updated_at, instance)

# # ================================
# # 2. Expense Change Signal (Update Property Story)
# # ================================

# # ================================
# # Expense: cache old status in pre_save
# # ================================
# @receiver(pre_save, sender=Expense)
# def cache_old_expense_status(sender, instance, **kwargs):
#     if not instance.pk:
#         _thread_locals.old_expense_status = None
#     else:
#         old_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
#         _thread_locals.old_expense_status = old_status


# # ================================
# # Expense: create story in post_save if status changed to approved
# # ================================
# @receiver(post_save, sender=Expense)
# def create_story_after_expense_approval(sender, instance, created, **kwargs):
#     if created:
#         # Skip new instances (no approval yet)
#         return

#     old_status = getattr(_thread_locals, 'old_expense_status', None)
#     new_status = instance.status
#     if old_status != 'approved' and new_status == 'approved':
#         prop = instance.property
#         if prop:
#             message = f"Expense approved: {instance.purpose} – {format_currency(instance.amount)} USD"
#             create_story(message, instance.updated_at, prop)