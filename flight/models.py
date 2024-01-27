from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

from datetime import datetime

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, user_type=None, **extra_fields):
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, user_type=user_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if 'first_name' not in extra_fields:
            extra_fields.setdefault('first_name', input('First name: '))
        if 'last_name' not in extra_fields:
            extra_fields.setdefault('last_name', input('Last name: '))
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        user_type = 'ADM'
        return self.create_user(username, email, password, user_type, **extra_fields)

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('EMP', 'Employee'),
        ('NOR', 'Normal'),
        ('ADM', 'Admin'),
    )
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    objects = UserManager()

    user_type = models.CharField(max_length=3, choices=USER_TYPE_CHOICES, default='NOR')

    def __str__(self):
        return f"{self.id}: {self.first_name} {self.last_name} : {self.user_type}"

class Place(models.Model):
    city = models.CharField(max_length=64)
    airport = models.CharField(max_length=64)
    code = models.CharField(max_length=3)
    country = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.city}, {self.country} ({self.code})"


class Week(models.Model):
    number = models.IntegerField()
    name = models.CharField(max_length=16)

    def __str__(self):
        return f"{self.name} ({self.number})"

FLIGHT_TYPE = {
    ('domestic', 'Domestic'),
    ('international', 'International')
}

class Flight(models.Model):
    type = models.CharField(max_length=16, choices=FLIGHT_TYPE)
    origin = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="departures")
    destination = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="arrivals")
    depart_time = models.TimeField(auto_now=False, auto_now_add=False)
    depart_day = models.ManyToManyField(Week, related_name="departure_flights_of_the_day")
    duration = models.DurationField(null=True)
    arrival_time = models.TimeField(auto_now=False, auto_now_add=False)
    arrival_day = models.ManyToManyField(Week, related_name="arrival_flights_of_the_day")
    plane = models.CharField(max_length=24)
    airline = models.CharField(max_length=64)
    economy_fare = models.FloatField(null=True)
    business_fare = models.FloatField(null=True)
    first_fare = models.FloatField(null=True)

    def __str__(self):
        return f"{self.id}: {self.origin} to {self.destination}"

    def save(self, *args, **kwargs):
        if self.id:
            self.type = 'domestic' if self.origin.country == self.destination.country else 'international'
            self.arrival_day.set([self.calculate_arrival_day()])
        super().save(*args, **kwargs)

    def calculate_arrival_day(self):
        depart_datetime = datetime.combine(datetime.today(), self.depart_time)
        arrival_datetime = depart_datetime + self.duration
        arrival_day_of_week = arrival_datetime.weekday()
        return Week.objects.get(number=arrival_day_of_week)


GENDER = (
    ('male','MALE'),    #(actual_value, human_readable_value)
    ('female','FEMALE')
)

class Passenger(models.Model):
    first_name = models.CharField(max_length=64, blank=True)
    last_name = models.CharField(max_length=64, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER, blank=True)
    #passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name="flights")
    #flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="passengers")

    def __str__(self):
        return f"Passenger: {self.first_name} {self.last_name}, {self.gender}"



SEAT_CLASS = (
    ('economy', 'Economy'),
    ('business', 'Business'),
    ('first', 'First')
)

TICKET_STATUS =(
    ('PENDING', 'Pending'),
    ('CONFIRMED', 'Confirmed'),
    ('CANCELLED', 'Cancelled')
)

class Ticket(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="bookings", blank=True, null=True)
    ref_no = models.CharField(max_length=6, unique=True)
    passengers = models.ManyToManyField(Passenger, related_name="flight_tickets")
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="tickets", blank=True, null=True)
    flight_ddate = models.DateField(blank=True, null=True)
    flight_adate = models.DateField(blank=True, null=True)
    flight_fare = models.FloatField(blank=True,null=True)
    other_charges = models.FloatField(blank=True,null=True)
    coupon_used = models.CharField(max_length=15,blank=True)
    coupon_discount = models.FloatField(default=0.0)
    total_fare = models.FloatField(blank=True, null=True)
    seat_class = models.CharField(max_length=20, choices=SEAT_CLASS)
    booking_date = models.DateTimeField(default=datetime.now)
    mobile = models.CharField(max_length=20,blank=True)
    email = models.EmailField(max_length=45, blank=True)
    status = models.CharField(max_length=45, choices=TICKET_STATUS)

    def __str__(self):
        return self.ref_no
