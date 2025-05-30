from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string

from django_otp.plugins.otp_totp.models import TOTPDevice

import os
import base64
import pyotp
from datetime import datetime, time, timedelta
import math

from .models import *
from capstone.utils import render_to_pdf, createticket


#Fee and Surcharge variable
from .constant import FEE
from flight.utils import createWeekDays, addPlaces, addDomesticFlights, addInternationalFlights

try:
    if len(Week.objects.all()) == 0:
        createWeekDays()

    if len(Place.objects.all()) == 0:
        addPlaces()

    if len(Flight.objects.all()) == 0:
        print("Do you want to add flights in the Database? (y/n)")
        if input().lower() in ['y', 'yes']:
            addDomesticFlights()
            addInternationalFlights()
except:
    pass

# Utility function

def get_flights_data(request, limit=None):
    direction = request.GET.get('direction', 'arrival')
    flight_type = request.GET.get('type', 'domestic')
    limit = limit or int(request.GET.get('limit', 10))
    week_day = Week.objects.get(number=datetime.now().weekday())
    if direction == 'arrival':
        flights = Flight.objects.filter(type=flight_type, arrival_day__in=[week_day]).order_by('arrival_time')[:limit]
    else:
        flights = Flight.objects.filter(type=flight_type, depart_day__in=[week_day]).order_by('depart_time')[:limit]
    if request.user and request.user.is_authenticated:
        tickets_data = Ticket.objects.filter(user=request.user).order_by('-booking_date')
        flight_places = Place.objects.all().order_by('code')
        flight_companies = sorted([fc['airline'] for fc in Flight.objects.values('airline').distinct()])
    else:
        tickets_data = []
        flight_places = []
        flight_companies = []
    return {
        'flights': flights,
        'current_time': datetime.now().strftime("%I:%M %p"),
        'count': len(flights),
        'direction': direction,
        'type': flight_type,
        'limit': limit,
        'week_day': week_day,
        'tickets': tickets_data,
        'flight_places': flight_places,
        'flight_companies': flight_companies,
        'week_days': Week.objects.all(),
    }

# Create your views here.

def index(request):
    min_date = f"{datetime.now().date().year}-{datetime.now().date().month}-{datetime.now().date().day}"
    max_date = f"{datetime.now().date().year if (datetime.now().date().month+3)<=12 else datetime.now().date().year+1}-{(datetime.now().date().month + 3) if (datetime.now().date().month+3)<=12 else (datetime.now().date().month+3-12)}-{datetime.now().date().day}"

    flight_data = get_flights_data(request, 10)

    if request.method == 'POST':
        origin = request.POST.get('Origin')
        destination = request.POST.get('Destination')
        depart_date = request.POST.get('DepartDate')
        seat = request.POST.get('SeatClass')
        trip_type = request.POST.get('TripType')
        if(trip_type == '1'):
            return render(request, 'flight/index.html', {
            'origin': origin,
            'destination': destination,
            'depart_date': depart_date,
            'seat': seat.lower(),
            'trip_type': trip_type,
            'flight_data': flight_data,
            'flight_data_limit': 10,
        })
        elif(trip_type == '2'):
            return_date = request.POST.get('ReturnDate')
            return render(request, 'flight/index.html', {
            'min_date': min_date,
            'max_date': max_date,
            'origin': origin,
            'destination': destination,
            'depart_date': depart_date,
            'seat': seat.lower(),
            'trip_type': trip_type,
            'return_date': return_date,
            'flight_data': flight_data,
        })
    else:
        return render(request, 'flight/index.html', {
            'min_date': min_date,
            'max_date': max_date,
            'flight_data': flight_data,
        })

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            devices = TOTPDevice.objects.filter(user=user, confirmed=True).first()
            request.session['user_id'] = user.id
            request.session['next_url'] = request.POST.get('next', '/')
            if devices:
                return redirect('totp_token_entry')
            else:
                return redirect('totp_device_setup')
        else:
            next_url = request.POST.get('next', '/')
            return render(request, "flight/login.html", {
                "message": "Invalid username and/or password.",
                "next": next_url
            })
    else:
        next_url = request.GET.get('next', '/')
        if request.user.is_authenticated:
            return redirect(next)
        else:
            return render(request, "flight/login.html", {
                "next": next_url
            })

def register_view(request):
    if request.method == "POST":
        fname = request.POST['firstname']
        lname = request.POST['lastname']
        username = request.POST["username"]
        email = request.POST["email"]
        user_type = request.POST["user_type"]
        return_json = request.POST.get("return_json", False)

        # Ensuring password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            if (return_json):
                return JsonResponse({'error': 'Passwords must match'})
            else :
                return render(request, "flight/register.html", {
                    "message": "Passwords must match."
                })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password, user_type)
            user.first_name = fname
            user.last_name = lname
            user.save()
        except:
            if return_json:
                return JsonResponse({'error': 'Username already taken'})
            else:
                return render(request, "flight/register.html", {
                    "message": "Username already taken."
                })
        if not return_json:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return JsonResponse({'success': True})
    else:
        return render(request, "flight/register.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def query(request, q):
    places = Place.objects.all()
    filters = []
    q = q.lower()
    for place in places:
        if (q in place.city.lower()) or (q in place.airport.lower()) or (q in place.code.lower()) or (q in place.country.lower()):
            filters.append(place)
    return JsonResponse([{'code':place.code, 'city':place.city, 'country': place.country} for place in filters], safe=False)

@csrf_exempt
def flight(request):
    o_place = request.GET.get('Origin')
    d_place = request.GET.get('Destination')
    trip_type = request.GET.get('TripType')
    departdate = request.GET.get('DepartDate')
    depart_date = datetime.strptime(departdate, "%Y-%m-%d")
    return_date = None
    if trip_type == '2':
        returndate = request.GET.get('ReturnDate')
        return_date = datetime.strptime(returndate, "%Y-%m-%d")
        flightday2 = Week.objects.get(number=return_date.weekday()) ##
        origin2 = Place.objects.get(code=d_place.upper())   ##
        destination2 = Place.objects.get(code=o_place.upper())  ##
    seat = request.GET.get('SeatClass')

    flightday = Week.objects.get(number=depart_date.weekday())
    destination = Place.objects.get(code=d_place.upper())
    origin = Place.objects.get(code=o_place.upper())
    if seat == 'economy':
        flights = Flight.objects.filter(depart_day=flightday,origin=origin,destination=destination).exclude(economy_fare=0).order_by('economy_fare')
        try:
            max_price = flights.last().economy_fare
            min_price = flights.first().economy_fare
        except:
            max_price = 0
            min_price = 0

        if trip_type == '2':    ##
            flights2 = Flight.objects.filter(depart_day=flightday2,origin=origin2,destination=destination2).exclude(economy_fare=0).order_by('economy_fare')    ##
            try:
                max_price2 = flights2.last().economy_fare   ##
                min_price2 = flights2.first().economy_fare  ##
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##

    elif seat == 'business':
        flights = Flight.objects.filter(depart_day=flightday,origin=origin,destination=destination).exclude(business_fare=0).order_by('business_fare')
        try:
            max_price = flights.last().business_fare
            min_price = flights.first().business_fare
        except:
            max_price = 0
            min_price = 0

        if trip_type == '2':    ##
            flights2 = Flight.objects.filter(depart_day=flightday2,origin=origin2,destination=destination2).exclude(business_fare=0).order_by('business_fare')    ##
            try:
                max_price2 = flights2.last().business_fare   ##
                min_price2 = flights2.first().business_fare  ##
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##

    elif seat == 'first':
        flights = Flight.objects.filter(depart_day=flightday,origin=origin,destination=destination).exclude(first_fare=0).order_by('first_fare')
        try:
            max_price = flights.last().first_fare
            min_price = flights.first().first_fare
        except:
            max_price = 0
            min_price = 0

        if trip_type == '2':    ##
            flights2 = Flight.objects.filter(depart_day=flightday2,origin=origin2,destination=destination2).exclude(first_fare=0).order_by('first_fare')
            try:
                max_price2 = flights2.last().first_fare   ##
                min_price2 = flights2.first().first_fare  ##
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##    ##

    #print(calendar.day_name[depart_date.weekday()])
    if trip_type == '2':
        return render(request, "flight/search.html", {
            'flights': flights,
            'origin': origin,
            'destination': destination,
            'flights2': flights2,   ##
            'origin2': origin2,    ##
            'destination2': destination2,    ##
            'seat': seat.capitalize(),
            'trip_type': trip_type,
            'depart_date': depart_date,
            'return_date': return_date,
            'max_price': math.ceil(max_price/100)*100,
            'min_price': math.floor(min_price/100)*100,
            'max_price2': math.ceil(max_price2/100)*100,    ##
            'min_price2': math.floor(min_price2/100)*100    ##
        })
    else:
        return render(request, "flight/search.html", {
            'flights': flights,
            'origin': origin,
            'destination': destination,
            'seat': seat.capitalize(),
            'trip_type': trip_type,
            'depart_date': depart_date,
            'return_date': return_date,
            'max_price': math.ceil(max_price/100)*100,
            'min_price': math.floor(min_price/100)*100
        })

def flight_chart(request):
    return render(request, 'flight/flight_chart_all.html', {
        'flight_data': get_flights_data(request, 50),
        'no_all_flights': True,
    })

def flight_chart_table(request):
    return HttpResponse(render_to_string('flight/flight_chart_table.html', {
        'flight_data': get_flights_data(request)
    }))

@login_required
def confirm_booking(request):
    flight_id = request.GET.get('flight_id')
    try:
        flight = Flight.objects.get(id=int(flight_id))
    except Flight.DoesNotExist as e:
        return JsonResponse({'message': 'Flight not found'})
    if flight:
        return render(request, "flight/book.html", {
            'flight1': flight,
            'fee': FEE,
            'seat': request.GET.get('seat_class', 'Economy'),
        })
    else:
        return JsonResponse({'message': 'Flight not found!'})


def review(request):
    flight_1 = request.GET.get('flight1Id')
    date1 = request.GET.get('flight1Date')
    seat = request.GET.get('seatClass')
    round_trip = False
    if request.GET.get('flight2Id'):
        round_trip = True

    if round_trip:
        flight_2 = request.GET.get('flight2Id')
        date2 = request.GET.get('flight2Date')

    if request.user.is_authenticated:
        flight1 = Flight.objects.get(id=flight_1)
        flight1ddate = datetime(int(date1.split('-')[2]),int(date1.split('-')[1]),int(date1.split('-')[0]),flight1.depart_time.hour,flight1.depart_time.minute)
        flight1adate = (flight1ddate + flight1.duration)
        flight2 = None
        flight2ddate = None
        flight2adate = None
        if round_trip:
            flight2 = Flight.objects.get(id=flight_2)
            flight2ddate = datetime(int(date2.split('-')[2]),int(date2.split('-')[1]),int(date2.split('-')[0]),flight2.depart_time.hour,flight2.depart_time.minute)
            flight2adate = (flight2ddate + flight2.duration)
        #print("//////////////////////////////////")
        #print(f"flight1ddate: {flight1adate-flight1ddate}")
        #print("//////////////////////////////////")
        if round_trip:
            return render(request, "flight/book.html", {
                'flight1': flight1,
                'flight2': flight2,
                "flight1ddate": flight1ddate,
                "flight1adate": flight1adate,
                "flight2ddate": flight2ddate,
                "flight2adate": flight2adate,
                "seat": seat,
                "fee": FEE
            })
        return render(request, "flight/book.html", {
            'flight1': flight1,
            "flight1ddate": flight1ddate,
            "flight1adate": flight1adate,
            "seat": seat,
            "fee": FEE
        })
    else:
        return HttpResponseRedirect(reverse("login"))

def book(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            flight_1 = request.POST.get('flight1')
            flight_1date = request.POST.get('flight1Date') or datetime.combine(datetime.today(), time())
            flight_1class = request.POST.get('flight1Class')
            f2 = False
            if request.POST.get('flight2'):
                flight_2 = request.POST.get('flight2')
                flight_2date = request.POST.get('flight2Date')
                flight_2class = request.POST.get('flight2Class')
                f2 = True
            countrycode = request.POST['countryCode']
            mobile = request.POST['mobile']
            email = request.POST['email']
            flight1 = Flight.objects.get(id=flight_1)
            if f2:
                flight2 = Flight.objects.get(id=flight_2)
            passengerscount = request.POST['passengersCount']
            passengers=[]
            for i in range(1,int(passengerscount)+1):
                fname = request.POST[f'passenger{i}FName']
                lname = request.POST[f'passenger{i}LName']
                gender = request.POST[f'passenger{i}Gender']
                passengers.append(Passenger.objects.create(first_name=fname,last_name=lname,gender=gender.lower()))
            coupon = request.POST.get('coupon')

            try:
                ticket1 = createticket(request.user,passengers,passengerscount,flight1,flight_1date,flight_1class,coupon,countrycode,email,mobile)
                if f2:
                    ticket2 = createticket(request.user,passengers,passengerscount,flight2,flight_2date,flight_2class,coupon,countrycode,email,mobile)

                if(flight_1class == 'Economy'):
                    if f2:
                        fare = (flight1.economy_fare*int(passengerscount))+(flight2.economy_fare*int(passengerscount))
                    else:
                        fare = flight1.economy_fare*int(passengerscount)
                elif (flight_1class == 'Business'):
                    if f2:
                        fare = (flight1.business_fare*int(passengerscount))+(flight2.business_fare*int(passengerscount))
                    else:
                        fare = flight1.business_fare*int(passengerscount)
                elif (flight_1class == 'First'):
                    if f2:
                        fare = (flight1.first_fare*int(passengerscount))+(flight2.first_fare*int(passengerscount))
                    else:
                        fare = flight1.first_fare*int(passengerscount)
            except Exception as e:
                return HttpResponse(e)


            if f2:    ##
                return render(request, "flight/payment.html", { ##
                    'fare': fare+FEE,   ##
                    'ticket': ticket1.id,   ##
                    'ticket2': ticket2.id   ##
                })  ##
            return render(request, "flight/payment.html", {
                'fare': fare+FEE,
                'ticket': ticket1.id
            })
        else:
            return HttpResponseRedirect(reverse("login"))
    else:
        return HttpResponse("Method must be post.")

def payment(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            ticket_id = request.POST['ticket']
            t2 = False
            if request.POST.get('ticket2'):
                ticket2_id = request.POST['ticket2']
                t2 = True
            fare = request.POST.get('fare')
            card_number = request.POST['cardNumber']
            card_holder_name = request.POST['cardHolderName']
            exp_month = request.POST['expMonth']
            exp_year = request.POST['expYear']
            cvv = request.POST['cvv']

            try:
                ticket = Ticket.objects.get(id=ticket_id)
                ticket.status = 'CONFIRMED'
                ticket.booking_date = datetime.now()
                ticket.save()
                if t2:
                    ticket2 = Ticket.objects.get(id=ticket2_id)
                    ticket2.status = 'CONFIRMED'
                    ticket2.save()
                    return render(request, 'flight/payment_process.html', {
                        'ticket1': ticket,
                        'ticket2': ticket2
                    })
                return render(request, 'flight/payment_process.html', {
                    'ticket1': ticket,
                    'ticket2': ""
                })
            except Exception as e:
                return HttpResponse(e)
        else:
            return HttpResponse("Method must be post.")
    else:
        return HttpResponseRedirect(reverse('login'))

@login_required
def add_flight(request):
    if request.method == 'POST':
        origin = Place.objects.get(code=request.POST['flightOrigin'].upper())
        destination = Place.objects.get(code=request.POST['flightDestination'].upper())
        depart_day = Week.objects.get(number=int(request.POST['flightDepartDay']))
        depart_time = datetime.strptime(request.POST['flightDepartTime'], "%H:%M").time()
        arrival_time = datetime.strptime(request.POST['flightArrivalTime'], "%H:%M").time()
        duration = request.POST['flightDuration']
        hours, minutes = map(int, duration.split(':'))
        duration = timedelta(hours=hours, minutes=minutes)
        company = request.POST['flightCompany']
        flight_no = request.POST['flightNo']
        economy_fare = float(request.POST['economyClassFare'])
        first_class_fare = float(request.POST['firstClassFare'])
        business_class_fare = float(request.POST['businessClassFare'])

        try:
            new_flight = Flight.objects.create(
                origin=origin,
                destination=destination,
                depart_time=depart_time,
                arrival_time=arrival_time,
                duration=duration,
                airline=company,
                plane=flight_no,
                economy_fare=economy_fare,
                first_fare=first_class_fare,
                business_fare=business_class_fare
            )
            new_flight.save()
            new_flight.depart_day.set([depart_day])
            new_flight.save()
            return JsonResponse({'success': 'Flight Created Successfully'})
        except Exception as e:
            return JsonResponse({'error': 'Error creating flight'})


def ticket_data(request, ref):
    ticket = Ticket.objects.get(ref_no=ref)
    return JsonResponse({
        'ref': ticket.ref_no,
        'from': ticket.flight.origin.code,
        'to': ticket.flight.destination.code,
        'flight_date': ticket.flight_ddate,
        'status': ticket.status
    })

@csrf_exempt
def get_ticket(request):
    ref = request.GET.get("ref")
    ticket1 = Ticket.objects.get(ref_no=ref)
    data = {
        'ticket1':ticket1,
        'current_year': datetime.now().year
    }
    pdf = render_to_pdf('flight/ticket.html', data)
    return HttpResponse(pdf, content_type='application/pdf')


def bookings(request):
    if request.user.is_authenticated:
        tickets = Ticket.objects.filter(user=request.user).order_by('-booking_date')
        return render(request, 'flight/bookings_wrapper.html', {
            'page': 'bookings',
            'tickets': tickets
        })
    else:
        return HttpResponseRedirect(reverse('login'))

@csrf_exempt
def cancel_ticket(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            ref = request.POST['ref']
            try:
                ticket = Ticket.objects.get(ref_no=ref)
                if ticket.user == request.user:
                    ticket.status = 'CANCELLED'
                    ticket.save()
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({
                        'success': False,
                        'error': "User unauthorised"
                    })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': e
                })
        else:
            return HttpResponse("User unauthorised")
    else:
        return HttpResponse("Method must be POST.")

def resume_booking(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            ref = request.POST['ref']
            ticket = Ticket.objects.get(ref_no=ref)
            if ticket.user == request.user:
                return render(request, "flight/payment.html", {
                    'fare': ticket.total_fare,
                    'ticket': ticket.id
                })
            else:
                return HttpResponse("User unauthorised")
        else:
            return HttpResponseRedirect(reverse("login"))
    else:
        return HttpResponse("Method must be post.")

def contact(request):
    return render(request, 'flight/contact.html', {'page': 'contact'})

def privacy_policy(request):
    return render(request, 'flight/privacy-policy.html')

def terms_and_conditions(request):
    return render(request, 'flight/terms.html')

def about_us(request):
    return render(request, 'flight/about.html', {'page': 'aboutus'})

def totp_device_setup(request):
    user = User.objects.get(id=request.session['user_id'])
    device, created = TOTPDevice.objects.get_or_create(user=user, name='default')
    if request.method == 'POST':
        # User has scanned the QR code and entered their first token
        token = request.POST['token']
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            return redirect('totp_token_entry')
        else:
            # Invalid token
            base32_key = base64.b32encode(device.key.encode()).decode()
            totp = pyotp.TOTP(base32_key)
            provisioning_uri = totp.provisioning_uri(name=user.username, issuer_name='Starcity Airport')
            return render(request, 'flight/totp_device_setup.html', {
                'provisioning_uri': provisioning_uri,
                'error_message': 'Invalid token, Please try again.'
            })
    else:
        key = os.urandom(20)
        hex_key = key.hex()
        device.key = hex_key
        device.confirmed = False
        device.save()

        base32_key = base64.b32encode(key).decode()
        totp = pyotp.TOTP(base32_key)
        provisioning_uri = totp.provisioning_uri(name=user.username, issuer_name='Starcity Airport')
        return render(request, 'flight/totp_device_setup.html', {'provisioning_uri': provisioning_uri})

def totp_token_entry(request):
    if request.method == 'POST':
        # User has entered their token
        token = request.POST['token']
        user = User.objects.get(id=request.session['user_id'])
        device = TOTPDevice.objects.get(user=user, name='default')

        if device.verify_token(token):
            login(request, user)
            next_url = request.session.get('next_url', '/')
            return redirect(next_url)
        else:
            return render(request, 'flight/totp_device_setup.html', {
                'error_message': 'Invalid token, Please try again.'
            })
    else:
        # Display token entry form
        return render(request, 'flight/totp_device_setup.html')
