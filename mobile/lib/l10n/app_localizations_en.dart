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
    return 'Habari, $name';
  }

  @override
  String get homeSubtitle => 'Here\'s what\'s happening with your cleaning.';

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
  String get bookingConfirmed =>
      'Booking confirmed — we\'re finding you a verified cleaner.';

  @override
  String get bookingReference => 'Booking reference';

  @override
  String get findingProvider =>
      'We\'re finding a verified cleaner for you. Follow the progress below.';

  @override
  String get progress => 'Progress';

  @override
  String get yourCleaner => 'Your cleaner';

  @override
  String get awaitingCleaner =>
      'We\'re matching you with a verified cleaner. This usually takes a few minutes.';

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
  String get confirmCompletion => 'Confirm job completed';

  @override
  String get confirmCompletionBody =>
      'Happy with the cleaning? Confirm so we can close the booking.';

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
      'We can\'t reach the server. Check your connection.';

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
  String get statusCLOSED => 'Closed';

  @override
  String get statusCANCELLED => 'Cancelled';

  @override
  String get statusREASSIGNMENT_REQUIRED => 'Finding a cleaner';

  @override
  String get statusDISPUTED => 'Issue under review';

  @override
  String get paymentPENDING => 'Pending';

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
}
