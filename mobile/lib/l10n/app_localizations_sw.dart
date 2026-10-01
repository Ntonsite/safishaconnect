// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Swahili (`sw`).
class AppLocalizationsSw extends AppLocalizations {
  AppLocalizationsSw([String locale = 'sw']) : super(locale);

  @override
  String get tagline => 'Usafi wa kitaalamu, bila usumbufu.';

  @override
  String get taglineBody =>
      'Chagua huduma na muda unaokufaa. Tunakupangia msafishaji aliyethibitishwa anayekuja na vifaa vyake.';

  @override
  String get signIn => 'Ingia';

  @override
  String get signOut => 'Toka';

  @override
  String get createAccount => 'Fungua akaunti';

  @override
  String get identifier => 'Barua pepe au namba ya simu';

  @override
  String get password => 'Nenosiri';

  @override
  String get fullName => 'Jina kamili';

  @override
  String get phone => 'Namba ya simu';

  @override
  String get phoneHint => 'mf. 0712 345 678';

  @override
  String get emailOptional => 'Barua pepe (si lazima)';

  @override
  String get passwordHint => 'Angalau herufi 8, ikiwemo herufi na namba.';

  @override
  String get noAccount => 'Mgeni hapa? Fungua akaunti';

  @override
  String get haveAccount => 'Tayari una akaunti? Ingia';

  @override
  String get demoAccount => 'Tumia akaunti ya majaribio ya mteja';

  @override
  String get required => 'Sehemu hii ni lazima.';

  @override
  String get invalidPhone => 'Weka namba sahihi ya simu ya Tanzania.';

  @override
  String get invalidPassword => 'Angalau herufi 8, ikiwemo herufi na namba.';

  @override
  String hello(String name) {
    return 'Habari, $name';
  }

  @override
  String get homeSubtitle => 'Hiki ndicho kinachoendelea na usafi wako.';

  @override
  String get bookCleaning => 'Agiza usafi';

  @override
  String get upcoming => 'Zijazo na zinazoendelea';

  @override
  String get history => 'Historia';

  @override
  String get noActive => 'Hakuna usafi uliopangwa';

  @override
  String get noActiveBody => 'Agiza usafi na sisi tutashughulikia mengine.';

  @override
  String get noHistory => 'Bado hakuna oda zilizopita.';

  @override
  String get bookings => 'Oda';

  @override
  String get home => 'Nyumbani';

  @override
  String get profile => 'Wasifu';

  @override
  String get language => 'Lugha';

  @override
  String get chooseService => 'Ungependa kusafishiwa nini?';

  @override
  String fromPrice(String price) {
    return 'Kuanzia $price';
  }

  @override
  String get stepService => 'Huduma';

  @override
  String get stepDetails => 'Maelezo';

  @override
  String get stepLocation => 'Mahali';

  @override
  String get stepSchedule => 'Tarehe na saa';

  @override
  String get stepReview => 'Hakiki na lipa';

  @override
  String get propertyType => 'Aina ya makazi';

  @override
  String get size => 'Ukubwa';

  @override
  String get bedrooms => 'Vyumba vya kulala';

  @override
  String get bathrooms => 'Mabafu';

  @override
  String get addons => 'Huduma za ziada (si lazima)';

  @override
  String get area => 'Mtaa';

  @override
  String get chooseArea => 'Chagua eneo lako';

  @override
  String get address => 'Anwani / nyumba';

  @override
  String get landmark => 'Alama ya karibu (si lazima)';

  @override
  String get instructions => 'Maelekezo maalum (si lazima)';

  @override
  String get chooseDate => 'Chagua tarehe';

  @override
  String get chooseTime => 'Chagua saa ya kuanza';

  @override
  String get noSlots =>
      'Hakuna wasafishaji wanaopatikana siku hii. Tafadhali jaribu tarehe nyingine.';

  @override
  String get unavailable => 'Haipatikani';

  @override
  String get paymentMethod => 'Ungependa kulipa vipi?';

  @override
  String get cash => 'Taslimu baada ya huduma';

  @override
  String get cashHint => 'Mlipe msafishaji kazi ikishakamilika.';

  @override
  String get mobileMoney => 'Pesa kwa simu';

  @override
  String get card => 'Kadi';

  @override
  String get comingSoon => 'Inakuja hivi karibuni';

  @override
  String get materialsIncluded =>
      'Msafishaji wako atakuja na vifaa na dawa zote.';

  @override
  String get estimatedDuration => 'Muda unaokadiriwa';

  @override
  String get total => 'Jumla';

  @override
  String get fixedPrice => 'Bei maalum — hakuna gharama za ziada mlangoni.';

  @override
  String get continueLabel => 'Endelea';

  @override
  String get back => 'Rudi';

  @override
  String confirmBooking(String price) {
    return 'Thibitisha oda · $price';
  }

  @override
  String get bookingConfirmed =>
      'Oda imethibitishwa — tunakutafutia msafishaji aliyethibitishwa.';

  @override
  String get progress => 'Maendeleo';

  @override
  String get yourCleaner => 'Msafishaji wako';

  @override
  String get awaitingCleaner =>
      'Tunakuunganisha na msafishaji aliyethibitishwa. Kwa kawaida huchukua dakika chache.';

  @override
  String get call => 'Piga simu';

  @override
  String get details => 'Maelezo';

  @override
  String get when => 'Lini';

  @override
  String get where => 'Wapi';

  @override
  String get priceBreakdown => 'Mchanganuo wa bei';

  @override
  String get payment => 'Malipo';

  @override
  String get confirmCompletion => 'Thibitisha kazi imekamilika';

  @override
  String get confirmCompletionBody =>
      'Umeridhika na usafi? Thibitisha ili tufunge oda.';

  @override
  String get cancelBooking => 'Ghairi oda';

  @override
  String get cancelConfirm => 'Ghairi oda hii? Msafishaji wako atajulishwa.';

  @override
  String get keep => 'Usighairi';

  @override
  String get rateTitle => 'Usafi ulikuwaje?';

  @override
  String get rateComment => 'Andika maneno machache (si lazima)';

  @override
  String get submitReview => 'Tuma maoni';

  @override
  String get thanksReview => 'Asante kwa maoni yako!';

  @override
  String get yourReview => 'Maoni yako';

  @override
  String get retry => 'Jaribu tena';

  @override
  String get genericError => 'Hitilafu imetokea. Tafadhali jaribu tena.';

  @override
  String get networkError => 'Hatuwezi kufikia seva. Angalia mtandao wako.';

  @override
  String minutes(int count) {
    return 'dak $count';
  }

  @override
  String hoursMinutes(int hours, int minutes) {
    return 'saa $hours dak $minutes';
  }

  @override
  String rooms(int bedrooms, int bathrooms) {
    return 'Vyumba vya kulala $bedrooms · Mabafu $bathrooms';
  }

  @override
  String get verified => 'Amethibitishwa';

  @override
  String get statusPENDING_CONFIRMATION => 'Inasubiri uthibitisho';

  @override
  String get statusCONFIRMED => 'Imethibitishwa';

  @override
  String get statusFINDING_PROVIDER => 'Tunatafuta msafishaji';

  @override
  String get statusPROVIDER_ASSIGNED => 'Msafishaji amepangwa';

  @override
  String get statusPROVIDER_EN_ROUTE => 'Msafishaji yuko njiani';

  @override
  String get statusPROVIDER_ARRIVED => 'Msafishaji amefika';

  @override
  String get statusSERVICE_IN_PROGRESS => 'Usafi unaendelea';

  @override
  String get statusCOMPLETED_BY_PROVIDER =>
      'Imekamilika — tafadhali thibitisha';

  @override
  String get statusCUSTOMER_CONFIRMED => 'Kukamilika kumethibitishwa';

  @override
  String get statusCLOSED => 'Imefungwa';

  @override
  String get statusCANCELLED => 'Imeghairiwa';

  @override
  String get statusREASSIGNMENT_REQUIRED => 'Tunatafuta msafishaji';

  @override
  String get statusDISPUTED => 'Tatizo linashughulikiwa';

  @override
  String get paymentPENDING => 'Inasubiri';

  @override
  String get paymentPAID => 'Imelipwa';

  @override
  String get paymentFAILED => 'Imeshindikana';

  @override
  String get paymentREFUNDED => 'Imerejeshwa';

  @override
  String get paymentCANCELLED => 'Imeghairiwa';

  @override
  String get serverAddress => 'Seva';

  @override
  String get demoData => 'Data ya majaribio';
}
