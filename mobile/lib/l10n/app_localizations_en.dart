// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get tagline => 'Professional cleaning, without the hassle.';

  @override
  String get taglineBody =>
      'Choose your service and schedule. We assign a verified cleaner who brings their own equipment.';

  @override
  String get signIn => 'Sign in';

  @override
  String get signOut => 'Sign out';

  @override
  String get createAccount => 'Create account';

  @override
  String get identifier => 'Email or phone number';

  @override
  String get password => 'Password';

  @override
  String get fullName => 'Full name';

  @override
  String get phone => 'Mobile number';

  @override
  String get phoneHint => 'e.g. 0712 345 678';

  @override
  String get emailOptional => 'Email (optional)';

  @override
  String get passwordHint =>
      'At least 8 characters, with a letter and a number.';

  @override
  String get noAccount => 'New here? Create an account';

  @override
  String get haveAccount => 'Already have an account? Sign in';

  @override
  String get demoAccount => 'Use demo customer account';

  @override
  String get required => 'This field is required.';

  @override
  String get invalidPhone => 'Enter a valid Tanzanian mobile number.';

  @override
  String get invalidPassword =>
      'At least 8 characters, with a letter and a number.';

  @override
  String hello(String name) {
    return 'Hello, $name';
  }

  @override
  String get homeSubtitle => 'A clean home, on your schedule.';

  @override
  String get bookCleaning => 'Book a cleaning';

  @override
  String get upcoming => 'Upcoming & active';

  @override
  String get history => 'History';

  @override
  String get noActive => 'No upcoming cleanings';

  @override
  String get noActiveBody =>
      'Book a cleaning and we\'ll take care of the rest.';

  @override
  String get noHistory => 'No past bookings yet.';

  @override
  String get bookings => 'Bookings';

  @override
  String get home => 'Home';

  @override
  String get profile => 'Profile';

  @override
  String get language => 'Language';

  @override
  String get chooseService => 'What would you like cleaned?';

  @override
  String fromPrice(String price) {
    return 'From $price';
  }

  @override
  String get stepService => 'Service';

  @override
  String get stepDetails => 'Details';

  @override
  String get stepLocation => 'Location';

  @override
  String get stepSchedule => 'Date & time';

  @override
  String get stepReview => 'Review & pay';

  @override
  String get propertyType => 'Property type';

  @override
  String get size => 'Size';

  @override
  String get bedrooms => 'Bedrooms';

  @override
  String get bathrooms => 'Bathrooms';

  @override
  String get addons => 'Add extras (optional)';

  @override
  String get area => 'Neighbourhood';

  @override
  String get chooseArea => 'Choose your area';

  @override
  String get address => 'Street address / house';

  @override
  String get landmark => 'Nearby landmark (optional)';

  @override
  String get instructions => 'Special instructions (optional)';

  @override
  String get chooseDate => 'Choose a date';

  @override
  String get chooseTime => 'Choose a start time';

  @override
  String get noSlots =>
      'No cleaners are available on this day. Please try another date.';

  @override
  String get unavailable => 'Unavailable';

  @override
  String get paymentMethod => 'How would you like to pay?';

  @override
  String get cash => 'Cash after the service';

  @override
  String get cashHint => 'Pay your cleaner once the job is done.';

  @override
  String get mobileMoney => 'Mobile money';

  @override
  String get card => 'Card';

  @override
  String get comingSoon => 'Coming soon';

  @override
  String get materialsIncluded =>
      'Your cleaner brings all equipment and materials.';

  @override
  String get estimatedDuration => 'Estimated duration';

  @override
  String get total => 'Total';

  @override
  String get fixedPrice => 'Fixed price — no extra charges at your door.';

  @override
  String get continueLabel => 'Continue';

  @override
  String get back => 'Back';

  @override
  String confirmBooking(String price) {
    return 'Confirm booking · $price';
  }

  @override
  String get bookingConfirmed => 'Your cleaning is booked';

  @override
  String get bookingReference => 'Booking reference';

  @override
  String get findingProvider =>
      'We\'re finding an available verified cleaner for you. You can track every step of your booking.';

  @override
  String get progress => 'Progress';

  @override
  String get yourCleaner => 'Your cleaner';

  @override
  String get awaitingCleaner =>
      'We\'re checking verified providers available in your area. Your booking will update when a cleaner accepts.';

  @override
  String get call => 'Call';

  @override
  String get details => 'Details';

  @override
  String get when => 'When';

  @override
  String get where => 'Where';

  @override
  String get priceBreakdown => 'Price breakdown';

  @override
  String get payment => 'Payment';

  @override
  String get confirmCompletion => 'Confirm completion';

  @override
  String get confirmCompletionBody =>
      'Has your cleaning been completed successfully? Confirm below or let us know about a problem.';

  @override
  String get reportIssue => 'Report an issue';

  @override
  String get issueCategory => 'What went wrong?';

  @override
  String get issueDescription => 'Tell us what happened';

  @override
  String get issueDescriptionHint => 'Please enter at least 10 characters.';

  @override
  String get issueSent => 'Your issue has been sent to Safisha support.';

  @override
  String get issueQuality => 'Cleaning quality';

  @override
  String get issueLate => 'Late or no show';

  @override
  String get issueDamage => 'Damage';

  @override
  String get issueConduct => 'Provider conduct';

  @override
  String get issuePayment => 'Payment';

  @override
  String get issueOther => 'Other';

  @override
  String get sendIssue => 'Send issue';

  @override
  String get cancelBooking => 'Cancel booking';

  @override
  String get cancelConfirm =>
      'Cancel this booking? Your cleaner will be notified.';

  @override
  String get keep => 'Keep booking';

  @override
  String get rateTitle => 'How was your cleaning?';

  @override
  String get rateComment => 'Share a few words (optional)';

  @override
  String get submitReview => 'Submit review';

  @override
  String get thanksReview => 'Thanks for your feedback!';

  @override
  String get yourReview => 'Your review';

  @override
  String get retry => 'Try again';

  @override
  String get genericError => 'Something went wrong. Please try again.';

  @override
  String get networkError =>
      'We couldn\'t connect. Check your internet connection and try again.';

  @override
  String minutes(int count) {
    return '$count min';
  }

  @override
  String hoursMinutes(int hours, int minutes) {
    return '${hours}h ${minutes}m';
  }

  @override
  String rooms(int bedrooms, int bathrooms) {
    String _temp0 = intl.Intl.pluralLogic(
      bedrooms,
      locale: localeName,
      other: '$bedrooms bedrooms',
      one: '1 bedroom',
    );
    String _temp1 = intl.Intl.pluralLogic(
      bathrooms,
      locale: localeName,
      other: '$bathrooms bathrooms',
      one: '1 bathroom',
    );
    return '$_temp0 · $_temp1';
  }

  @override
  String get verified => 'Verified';

  @override
  String get statusPENDING_CONFIRMATION => 'Awaiting confirmation';

  @override
  String get statusCONFIRMED => 'Confirmed';

  @override
  String get statusFINDING_PROVIDER => 'Finding a cleaner';

  @override
  String get statusPROVIDER_ASSIGNED => 'Cleaner assigned';

  @override
  String get statusPROVIDER_EN_ROUTE => 'Cleaner on the way';

  @override
  String get statusPROVIDER_ARRIVED => 'Cleaner arrived';

  @override
  String get statusSERVICE_IN_PROGRESS => 'Cleaning in progress';

  @override
  String get statusCOMPLETED_BY_PROVIDER => 'Completed — please confirm';

  @override
  String get statusCUSTOMER_CONFIRMED => 'Completion confirmed';

  @override
  String get statusCLOSED => 'Completed';

  @override
  String get statusCANCELLED => 'Cancelled';

  @override
  String get statusREASSIGNMENT_REQUIRED => 'Finding a cleaner';

  @override
  String get statusDISPUTED => 'Issue under review';

  @override
  String get paymentPENDING => 'Pay after cleaning';

  @override
  String get paymentPAID => 'Paid';

  @override
  String get paymentFAILED => 'Failed';

  @override
  String get paymentREFUNDED => 'Refunded';

  @override
  String get paymentCANCELLED => 'Cancelled';

  @override
  String get serverAddress => 'Server';

  @override
  String get demoData => 'Demo data';

  @override
  String get materialsLine => 'Equipment & materials';

  @override
  String get included => 'Included';

  @override
  String get popularServices => 'Our cleaning services';

  @override
  String get howTitle => 'Book. We assign. We clean.';

  @override
  String get howBody =>
      'Choose your service and time. We assign a verified professional who brings the equipment. Pay in cash after cleaning.';

  @override
  String get activeBooking => 'Your next cleaning';

  @override
  String get trackBooking => 'Track booking';

  @override
  String get backHome => 'Back to home';

  @override
  String get bookAgain => 'Book again';

  @override
  String get allBookings => 'All';

  @override
  String get pastBookings => 'Past';

  @override
  String get noFilteredBookings => 'No bookings here yet';

  @override
  String get noFilteredBody =>
      'Your bookings will appear here when they match this filter.';

  @override
  String get loadingBookings => 'Loading your bookings…';

  @override
  String get loadingServices => 'Loading cleaning services…';

  @override
  String get loadingBooking => 'Loading your booking…';

  @override
  String get loadingSlots => 'Checking available times…';

  @override
  String get updatingPrice => 'Updating your price…';

  @override
  String get confirmingBooking => 'Confirming your booking…';

  @override
  String get serviceDetails => 'About this cleaning';

  @override
  String get serviceIncludes => 'What\'s included';

  @override
  String get selectService => 'Choose this service';

  @override
  String get locationTitle => 'Where do you need cleaning?';

  @override
  String get locationHint =>
      'Choose a supported neighbourhood in Dar es Salaam.';

  @override
  String get addressHint => 'Street, house or apartment number';

  @override
  String get addressValidation =>
      'Enter at least 3 characters for your address.';

  @override
  String get instructionsHint =>
      'Gate access or anything that needs special attention';

  @override
  String get reviewBooking => 'Review your cleaning';

  @override
  String get edit => 'Edit';

  @override
  String get confirmBookingLabel => 'Confirm booking';

  @override
  String get property => 'Property';

  @override
  String get paymentAfter => 'Cash — pay after cleaning';

  @override
  String get findingTitle => 'Finding your cleaning professional';

  @override
  String get assignedTitle => 'Your cleaner is confirmed';

  @override
  String get enRouteTitle => 'Your cleaner is on the way';

  @override
  String get arrivedTitle => 'Your cleaner has arrived';

  @override
  String get inProgressTitle => 'Cleaning in progress';

  @override
  String get completedTitle => 'Cleaning completed';

  @override
  String get assignedBody =>
      'Your professional is assigned for the date and time below. They bring their own equipment and materials.';

  @override
  String get enRouteBody =>
      'Your professional has marked that they are travelling to your address.';

  @override
  String get arrivedBody =>
      'Your professional has marked their arrival. Cleaning will begin next.';

  @override
  String get inProgressBody =>
      'Your professional is working on your cleaning. You can check progress here.';

  @override
  String get closedBody =>
      'Your cleaning is complete. Thank you for choosing SafishaCon.';

  @override
  String get cancelledBody =>
      'This booking was cancelled. You can book another cleaning whenever you are ready.';

  @override
  String get disputedBody => 'Our team is reviewing the issue you reported.';

  @override
  String get refreshBooking => 'Refresh booking';

  @override
  String get refreshFailed =>
      'We couldn\'t update the booking. The last received information is still shown.';

  @override
  String get contactDetails => 'Contact details';

  @override
  String get copyNumber => 'Copy number';

  @override
  String get numberCopied => 'Phone number copied';

  @override
  String get support => 'Need help?';

  @override
  String get supportBody =>
      'For booking questions, contact SafishaCon using the details below.';

  @override
  String get contactSupport => 'Support contact details';

  @override
  String get noSupportContact =>
      'Support contact details are currently unavailable. Please try again later.';

  @override
  String get accountDetails => 'Your account';

  @override
  String get signOutConfirm => 'Sign out of SafishaCon?';

  @override
  String get staySignedIn => 'Stay signed in';

  @override
  String get showPassword => 'Show password';

  @override
  String get hidePassword => 'Hide password';

  @override
  String get loginFailed =>
      'Check your email or phone number and password, then try again.';

  @override
  String get sessionExpired => 'Your session ended. Please sign in again.';

  @override
  String get customersOnly =>
      'This app is for customers. Providers and administrators use the web portal.';

  @override
  String get bookingUnavailable =>
      'This booking is no longer available. Return to your bookings and refresh.';

  @override
  String get slotUnavailable =>
      'This time is no longer available. Choose another time before confirming.';

  @override
  String get unsupportedArea =>
      'We don\'t serve this area yet. Please choose one of the listed neighbourhoods.';

  @override
  String get actionUnavailable =>
      'This booking has changed. Refresh it before trying again.';

  @override
  String get accountExists =>
      'An account with these contact details already exists. Try signing in.';

  @override
  String get invalidEmail => 'Enter a valid email address or leave it blank.';

  @override
  String get unknownStatus => 'Booking update';

  @override
  String ratingLabel(int count) {
    return '$count out of 5 stars';
  }

  @override
  String get cleaningPhotoAlt => 'A cleaning professional wiping a window.';

  @override
  String get startingApp => 'Preparing SafishaCon…';

  @override
  String get selected => 'Selected';
}
