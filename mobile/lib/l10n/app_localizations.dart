import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_sw.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('sw'),
  ];

  /// No description provided for @tagline.
  ///
  /// In en, this message translates to:
  /// **'Professional cleaning, without the hassle.'**
  String get tagline;

  /// No description provided for @taglineBody.
  ///
  /// In en, this message translates to:
  /// **'Choose your service and schedule. We assign a verified cleaner who brings their own equipment.'**
  String get taglineBody;

  /// No description provided for @signIn.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get signIn;

  /// No description provided for @signOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get signOut;

  /// No description provided for @createAccount.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get createAccount;

  /// No description provided for @identifier.
  ///
  /// In en, this message translates to:
  /// **'Email or phone number'**
  String get identifier;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @fullName.
  ///
  /// In en, this message translates to:
  /// **'Full name'**
  String get fullName;

  /// No description provided for @phone.
  ///
  /// In en, this message translates to:
  /// **'Mobile number'**
  String get phone;

  /// No description provided for @phoneHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. 0712 345 678'**
  String get phoneHint;

  /// No description provided for @emailOptional.
  ///
  /// In en, this message translates to:
  /// **'Email (optional)'**
  String get emailOptional;

  /// No description provided for @passwordHint.
  ///
  /// In en, this message translates to:
  /// **'At least 8 characters, with a letter and a number.'**
  String get passwordHint;

  /// No description provided for @noAccount.
  ///
  /// In en, this message translates to:
  /// **'New here? Create an account'**
  String get noAccount;

  /// No description provided for @haveAccount.
  ///
  /// In en, this message translates to:
  /// **'Already have an account? Sign in'**
  String get haveAccount;

  /// No description provided for @demoAccount.
  ///
  /// In en, this message translates to:
  /// **'Use demo customer account'**
  String get demoAccount;

  /// No description provided for @required.
  ///
  /// In en, this message translates to:
  /// **'This field is required.'**
  String get required;

  /// No description provided for @invalidPhone.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid Tanzanian mobile number.'**
  String get invalidPhone;

  /// No description provided for @invalidPassword.
  ///
  /// In en, this message translates to:
  /// **'At least 8 characters, with a letter and a number.'**
  String get invalidPassword;

  /// No description provided for @hello.
  ///
  /// In en, this message translates to:
  /// **'Habari, {name}'**
  String hello(String name);

  /// No description provided for @homeSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Here\'s what\'s happening with your cleaning.'**
  String get homeSubtitle;

  /// No description provided for @bookCleaning.
  ///
  /// In en, this message translates to:
  /// **'Book a cleaning'**
  String get bookCleaning;

  /// No description provided for @upcoming.
  ///
  /// In en, this message translates to:
  /// **'Upcoming & active'**
  String get upcoming;

  /// No description provided for @history.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get history;

  /// No description provided for @noActive.
  ///
  /// In en, this message translates to:
  /// **'No upcoming cleanings'**
  String get noActive;

  /// No description provided for @noActiveBody.
  ///
  /// In en, this message translates to:
  /// **'Book a cleaning and we\'ll take care of the rest.'**
  String get noActiveBody;

  /// No description provided for @noHistory.
  ///
  /// In en, this message translates to:
  /// **'No past bookings yet.'**
  String get noHistory;

  /// No description provided for @bookings.
  ///
  /// In en, this message translates to:
  /// **'Bookings'**
  String get bookings;

  /// No description provided for @home.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get home;

  /// No description provided for @profile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profile;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @chooseService.
  ///
  /// In en, this message translates to:
  /// **'What would you like cleaned?'**
  String get chooseService;

  /// No description provided for @fromPrice.
  ///
  /// In en, this message translates to:
  /// **'From {price}'**
  String fromPrice(String price);

  /// No description provided for @stepService.
  ///
  /// In en, this message translates to:
  /// **'Service'**
  String get stepService;

  /// No description provided for @stepDetails.
  ///
  /// In en, this message translates to:
  /// **'Details'**
  String get stepDetails;

  /// No description provided for @stepLocation.
  ///
  /// In en, this message translates to:
  /// **'Location'**
  String get stepLocation;

  /// No description provided for @stepSchedule.
  ///
  /// In en, this message translates to:
  /// **'Date & time'**
  String get stepSchedule;

  /// No description provided for @stepReview.
  ///
  /// In en, this message translates to:
  /// **'Review & pay'**
  String get stepReview;

  /// No description provided for @propertyType.
  ///
  /// In en, this message translates to:
  /// **'Property type'**
  String get propertyType;

  /// No description provided for @size.
  ///
  /// In en, this message translates to:
  /// **'Size'**
  String get size;

  /// No description provided for @bedrooms.
  ///
  /// In en, this message translates to:
  /// **'Bedrooms'**
  String get bedrooms;

  /// No description provided for @bathrooms.
  ///
  /// In en, this message translates to:
  /// **'Bathrooms'**
  String get bathrooms;

  /// No description provided for @addons.
  ///
  /// In en, this message translates to:
  /// **'Add extras (optional)'**
  String get addons;

  /// No description provided for @area.
  ///
  /// In en, this message translates to:
  /// **'Neighbourhood'**
  String get area;

  /// No description provided for @chooseArea.
  ///
  /// In en, this message translates to:
  /// **'Choose your area'**
  String get chooseArea;

  /// No description provided for @address.
  ///
  /// In en, this message translates to:
  /// **'Street address / house'**
  String get address;

  /// No description provided for @landmark.
  ///
  /// In en, this message translates to:
  /// **'Nearby landmark (optional)'**
  String get landmark;

  /// No description provided for @instructions.
  ///
  /// In en, this message translates to:
  /// **'Special instructions (optional)'**
  String get instructions;

  /// No description provided for @chooseDate.
  ///
  /// In en, this message translates to:
  /// **'Choose a date'**
  String get chooseDate;

  /// No description provided for @chooseTime.
  ///
  /// In en, this message translates to:
  /// **'Choose a start time'**
  String get chooseTime;

  /// No description provided for @noSlots.
  ///
  /// In en, this message translates to:
  /// **'No cleaners are available on this day. Please try another date.'**
  String get noSlots;

  /// No description provided for @unavailable.
  ///
  /// In en, this message translates to:
  /// **'Unavailable'**
  String get unavailable;

  /// No description provided for @paymentMethod.
  ///
  /// In en, this message translates to:
  /// **'How would you like to pay?'**
  String get paymentMethod;

  /// No description provided for @cash.
  ///
  /// In en, this message translates to:
  /// **'Cash after the service'**
  String get cash;

  /// No description provided for @cashHint.
  ///
  /// In en, this message translates to:
  /// **'Pay your cleaner once the job is done.'**
  String get cashHint;

  /// No description provided for @mobileMoney.
  ///
  /// In en, this message translates to:
  /// **'Mobile money'**
  String get mobileMoney;

  /// No description provided for @card.
  ///
  /// In en, this message translates to:
  /// **'Card'**
  String get card;

  /// No description provided for @comingSoon.
  ///
  /// In en, this message translates to:
  /// **'Coming soon'**
  String get comingSoon;

  /// No description provided for @materialsIncluded.
  ///
  /// In en, this message translates to:
  /// **'Your cleaner brings all equipment and materials.'**
  String get materialsIncluded;

  /// No description provided for @estimatedDuration.
  ///
  /// In en, this message translates to:
  /// **'Estimated duration'**
  String get estimatedDuration;

  /// No description provided for @total.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get total;

  /// No description provided for @fixedPrice.
  ///
  /// In en, this message translates to:
  /// **'Fixed price — no extra charges at your door.'**
  String get fixedPrice;

  /// No description provided for @continueLabel.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueLabel;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @confirmBooking.
  ///
  /// In en, this message translates to:
  /// **'Confirm booking · {price}'**
  String confirmBooking(String price);

  /// No description provided for @bookingConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Booking confirmed — we\'re finding you a verified cleaner.'**
  String get bookingConfirmed;

  /// No description provided for @bookingReference.
  ///
  /// In en, this message translates to:
  /// **'Booking reference'**
  String get bookingReference;

  /// No description provided for @findingProvider.
  ///
  /// In en, this message translates to:
  /// **'We\'re finding a verified cleaner for you. Follow the progress below.'**
  String get findingProvider;

  /// No description provided for @progress.
  ///
  /// In en, this message translates to:
  /// **'Progress'**
  String get progress;

  /// No description provided for @yourCleaner.
  ///
  /// In en, this message translates to:
  /// **'Your cleaner'**
  String get yourCleaner;

  /// No description provided for @awaitingCleaner.
  ///
  /// In en, this message translates to:
  /// **'We\'re matching you with a verified cleaner. This usually takes a few minutes.'**
  String get awaitingCleaner;

  /// No description provided for @call.
  ///
  /// In en, this message translates to:
  /// **'Call'**
  String get call;

  /// No description provided for @details.
  ///
  /// In en, this message translates to:
  /// **'Details'**
  String get details;

  /// No description provided for @when.
  ///
  /// In en, this message translates to:
  /// **'When'**
  String get when;

  /// No description provided for @where.
  ///
  /// In en, this message translates to:
  /// **'Where'**
  String get where;

  /// No description provided for @priceBreakdown.
  ///
  /// In en, this message translates to:
  /// **'Price breakdown'**
  String get priceBreakdown;

  /// No description provided for @payment.
  ///
  /// In en, this message translates to:
  /// **'Payment'**
  String get payment;

  /// No description provided for @confirmCompletion.
  ///
  /// In en, this message translates to:
  /// **'Confirm job completed'**
  String get confirmCompletion;

  /// No description provided for @confirmCompletionBody.
  ///
  /// In en, this message translates to:
  /// **'Happy with the cleaning? Confirm so we can close the booking.'**
  String get confirmCompletionBody;

  /// No description provided for @reportIssue.
  ///
  /// In en, this message translates to:
  /// **'Report an issue'**
  String get reportIssue;

  /// No description provided for @issueCategory.
  ///
  /// In en, this message translates to:
  /// **'What went wrong?'**
  String get issueCategory;

  /// No description provided for @issueDescription.
  ///
  /// In en, this message translates to:
  /// **'Tell us what happened'**
  String get issueDescription;

  /// No description provided for @issueDescriptionHint.
  ///
  /// In en, this message translates to:
  /// **'Please enter at least 10 characters.'**
  String get issueDescriptionHint;

  /// No description provided for @issueSent.
  ///
  /// In en, this message translates to:
  /// **'Your issue has been sent to Safisha support.'**
  String get issueSent;

  /// No description provided for @issueQuality.
  ///
  /// In en, this message translates to:
  /// **'Cleaning quality'**
  String get issueQuality;

  /// No description provided for @issueLate.
  ///
  /// In en, this message translates to:
  /// **'Late or no show'**
  String get issueLate;

  /// No description provided for @issueDamage.
  ///
  /// In en, this message translates to:
  /// **'Damage'**
  String get issueDamage;

  /// No description provided for @issueConduct.
  ///
  /// In en, this message translates to:
  /// **'Provider conduct'**
  String get issueConduct;

  /// No description provided for @issuePayment.
  ///
  /// In en, this message translates to:
  /// **'Payment'**
  String get issuePayment;

  /// No description provided for @issueOther.
  ///
  /// In en, this message translates to:
  /// **'Other'**
  String get issueOther;

  /// No description provided for @sendIssue.
  ///
  /// In en, this message translates to:
  /// **'Send issue'**
  String get sendIssue;

  /// No description provided for @cancelBooking.
  ///
  /// In en, this message translates to:
  /// **'Cancel booking'**
  String get cancelBooking;

  /// No description provided for @cancelConfirm.
  ///
  /// In en, this message translates to:
  /// **'Cancel this booking? Your cleaner will be notified.'**
  String get cancelConfirm;

  /// No description provided for @keep.
  ///
  /// In en, this message translates to:
  /// **'Keep booking'**
  String get keep;

  /// No description provided for @rateTitle.
  ///
  /// In en, this message translates to:
  /// **'How was your cleaning?'**
  String get rateTitle;

  /// No description provided for @rateComment.
  ///
  /// In en, this message translates to:
  /// **'Share a few words (optional)'**
  String get rateComment;

  /// No description provided for @submitReview.
  ///
  /// In en, this message translates to:
  /// **'Submit review'**
  String get submitReview;

  /// No description provided for @thanksReview.
  ///
  /// In en, this message translates to:
  /// **'Thanks for your feedback!'**
  String get thanksReview;

  /// No description provided for @yourReview.
  ///
  /// In en, this message translates to:
  /// **'Your review'**
  String get yourReview;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get retry;

  /// No description provided for @genericError.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Please try again.'**
  String get genericError;

  /// No description provided for @networkError.
  ///
  /// In en, this message translates to:
  /// **'We can\'t reach the server. Check your connection.'**
  String get networkError;

  /// No description provided for @minutes.
  ///
  /// In en, this message translates to:
  /// **'{count} min'**
  String minutes(int count);

  /// No description provided for @hoursMinutes.
  ///
  /// In en, this message translates to:
  /// **'{hours}h {minutes}m'**
  String hoursMinutes(int hours, int minutes);

  /// No description provided for @rooms.
  ///
  /// In en, this message translates to:
  /// **'{bedrooms, plural, =1{1 bedroom} other{{bedrooms} bedrooms}} · {bathrooms, plural, =1{1 bathroom} other{{bathrooms} bathrooms}}'**
  String rooms(int bedrooms, int bathrooms);

  /// No description provided for @verified.
  ///
  /// In en, this message translates to:
  /// **'Verified'**
  String get verified;

  /// No description provided for @statusPENDING_CONFIRMATION.
  ///
  /// In en, this message translates to:
  /// **'Awaiting confirmation'**
  String get statusPENDING_CONFIRMATION;

  /// No description provided for @statusCONFIRMED.
  ///
  /// In en, this message translates to:
  /// **'Confirmed'**
  String get statusCONFIRMED;

  /// No description provided for @statusFINDING_PROVIDER.
  ///
  /// In en, this message translates to:
  /// **'Finding a cleaner'**
  String get statusFINDING_PROVIDER;

  /// No description provided for @statusPROVIDER_ASSIGNED.
  ///
  /// In en, this message translates to:
  /// **'Cleaner assigned'**
  String get statusPROVIDER_ASSIGNED;

  /// No description provided for @statusPROVIDER_EN_ROUTE.
  ///
  /// In en, this message translates to:
  /// **'Cleaner on the way'**
  String get statusPROVIDER_EN_ROUTE;

  /// No description provided for @statusPROVIDER_ARRIVED.
  ///
  /// In en, this message translates to:
  /// **'Cleaner arrived'**
  String get statusPROVIDER_ARRIVED;

  /// No description provided for @statusSERVICE_IN_PROGRESS.
  ///
  /// In en, this message translates to:
  /// **'Cleaning in progress'**
  String get statusSERVICE_IN_PROGRESS;

  /// No description provided for @statusCOMPLETED_BY_PROVIDER.
  ///
  /// In en, this message translates to:
  /// **'Completed — please confirm'**
  String get statusCOMPLETED_BY_PROVIDER;

  /// No description provided for @statusCUSTOMER_CONFIRMED.
  ///
  /// In en, this message translates to:
  /// **'Completion confirmed'**
  String get statusCUSTOMER_CONFIRMED;

  /// No description provided for @statusCLOSED.
  ///
  /// In en, this message translates to:
  /// **'Closed'**
  String get statusCLOSED;

  /// No description provided for @statusCANCELLED.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get statusCANCELLED;

  /// No description provided for @statusREASSIGNMENT_REQUIRED.
  ///
  /// In en, this message translates to:
  /// **'Finding a cleaner'**
  String get statusREASSIGNMENT_REQUIRED;

  /// No description provided for @statusDISPUTED.
  ///
  /// In en, this message translates to:
  /// **'Issue under review'**
  String get statusDISPUTED;

  /// No description provided for @paymentPENDING.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get paymentPENDING;

  /// No description provided for @paymentPAID.
  ///
  /// In en, this message translates to:
  /// **'Paid'**
  String get paymentPAID;

  /// No description provided for @paymentFAILED.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get paymentFAILED;

  /// No description provided for @paymentREFUNDED.
  ///
  /// In en, this message translates to:
  /// **'Refunded'**
  String get paymentREFUNDED;

  /// No description provided for @paymentCANCELLED.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get paymentCANCELLED;

  /// No description provided for @serverAddress.
  ///
  /// In en, this message translates to:
  /// **'Server'**
  String get serverAddress;

  /// No description provided for @demoData.
  ///
  /// In en, this message translates to:
  /// **'Demo data'**
  String get demoData;

  /// No description provided for @materialsLine.
  ///
  /// In en, this message translates to:
  /// **'Equipment & materials'**
  String get materialsLine;

  /// No description provided for @included.
  ///
  /// In en, this message translates to:
  /// **'Included'**
  String get included;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'sw'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'sw':
      return AppLocalizationsSw();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
