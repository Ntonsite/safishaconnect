import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../core/repository.dart';
import '../../core/api_client.dart';
import '../../l10n/app_localizations.dart';
import '../../models/models.dart';
import '../../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/service_widgets.dart';

/// Five-step booking flow. Prices, durations and slots all come from the API.

class BookingFlowScreen extends StatefulWidget {
  final Service? initialService;
  final BookingDetail? repeatBooking;
  const BookingFlowScreen({super.key, this.initialService, this.repeatBooking});

  @override
  State<BookingFlowScreen> createState() => _BookingFlowScreenState();
}

class _BookingFlowScreenState extends State<BookingFlowScreen> {
  int _step = 0;
  int _quoteRevision = 0;
  int _slotRevision = 0;
  Object? _slotsError;
  final _scroll = ScrollController();
  List<Service>? _services;
  List<Area>? _areas;
  Object? _loadError;
  Service? _service;
  String? _propertyTypeId;
  String? _sizeId;
  int _bedrooms = 1;
  int _bathrooms = 1;
  final Map<String, int> _addons = {};
  String? _areaId;
  final _address = TextEditingController();
  final _landmark = TextEditingController();
  final _instructions = TextEditingController();
  late DateTime _date;
  String? _time;
  Quote? _quote;
  Object? _quoteError;
  bool _quoting = false;
  Timer? _debounce;
  List<Slot>? _slots;
  bool _loadingSlots = false;
  bool _submitting = false;
  String? _submissionKey;
  String? _submissionBody;
  Repository get _repo => context.read<Repository>();

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _date = DateTime(now.year, now.month, now.day + 1);
    final me = context.read<AppState>().me;
    _areaId = me?.defaultAreaId;
    _address.text = me?.defaultAddress ?? '';
    _loadCatalogue();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _scroll.dispose();
    _address.dispose();
    _landmark.dispose();
    _instructions.dispose();
    super.dispose();
  }

  Future<void> _loadCatalogue() async {
    setState(() => _loadError = null);
    try {
      final results = await Future.wait([_repo.services(), _repo.areas()]);
      if (!mounted) return;
      setState(() {
        _services = results[0] as List<Service>;
        _areas = results[1] as List<Area>;
        if (_areaId != null && !_areas!.any((a) => a.id == _areaId)) {
          _areaId = null;
        }
      });
      final initial =
          widget.initialService?.id ?? widget.repeatBooking?.service['id'];
      final selected = _services!.where((s) => s.id == initial).firstOrNull;
      if (selected != null) {
        _chooseService(selected);
        final repeat = widget.repeatBooking;
        if (repeat != null) {
          _bedrooms = repeat.bedrooms.clamp(0, selected.maxRooms);
          _bathrooms = repeat.bathrooms.clamp(1, selected.maxRooms);
          if (selected.options.any((o) => o.id == repeat.propertyType?['id'])) {
            _propertyTypeId = repeat.propertyType?['id'];
          }
          if (selected.options.any((o) => o.id == repeat.size?['id'])) {
            _sizeId = repeat.size?['id'];
          }
          if (_areas!.any((a) => a.id == repeat.areaId)) {
            _areaId = repeat.areaId;
          }
          _address.text = repeat.addressLine ?? '';
          _landmark.text = repeat.landmark ?? '';
          _requestQuote(immediate: true);
        }
      }
    } catch (e) {
      if (mounted) setState(() => _loadError = e);
    }
  }

  void _chooseService(Service s) {
    setState(() {
      _service = s;
      _propertyTypeId = s.group('PROPERTY_TYPE').firstOrNull?.id;
      _sizeId = s.group('SIZE').firstOrNull?.id;
      _bedrooms = s.includedBedrooms.clamp(1, s.maxRooms);
      _bathrooms = s.includedBathrooms.clamp(1, s.maxRooms);
      _addons.clear();
      _time = null;
      _quote = null;
      _step = 1;
    });
    if (_scroll.hasClients) _scroll.jumpTo(0);
    _requestQuote(immediate: true);
  }

  Map<String, dynamic> get _quoteRequest => {
    'service_id': _service!.id,
    'property_type_option_id': _propertyTypeId,
    'size_option_id': _sizeId,
    'bedrooms': _service!.usesRooms ? _bedrooms : 0,
    'bathrooms': _service!.usesRooms ? _bathrooms : 0,
    'addons': [
      for (final e in _addons.entries)
        if (e.value > 0) {'option_id': e.key, 'quantity': e.value},
    ],
  };
  void _requestQuote({bool immediate = false}) {
    _debounce?.cancel();
    final revision = ++_quoteRevision;
    final request = _quoteRequest;
    setState(() {
      _quoting = true;
      _quoteError = null;
      _time = null;
    });
    _debounce = Timer(Duration(milliseconds: immediate ? 0 : 250), () async {
      try {
        final q = await _repo.quote(request);
        if (mounted && revision == _quoteRevision) {
          setState(() {
            _quote = q;
            _quoteError = null;
          });
        }
      } catch (e) {
        if (mounted && revision == _quoteRevision) {
          setState(() {
            _quote = null;
            _quoteError = e;
          });
        }
      } finally {
        if (mounted && revision == _quoteRevision) {
          setState(() => _quoting = false);
        }
      }
    });
  }

  Future<void> _loadSlots() async {
    if (_quote == null || _areaId == null) return;
    final revision = ++_slotRevision;
    setState(() {
      _loadingSlots = true;
      _slots = null;
      _slotsError = null;
      _time = null;
    });
    try {
      final slots = await _repo.slots(
        serviceId: _service!.id,
        areaId: _areaId!,
        date: DateFormat('yyyy-MM-dd').format(_date),
        durationMinutes: _quote!.durationMinutes,
      );
      if (!mounted || revision != _slotRevision) return;
      setState(() {
        _slots = slots;
        if (_time != null &&
            !slots.any((s) => s.start == _time && s.available)) {
          _time = null;
        }
      });
    } catch (e) {
      if (mounted && revision == _slotRevision) setState(() => _slotsError = e);
    } finally {
      if (mounted && revision == _slotRevision) {
        setState(() => _loadingSlots = false);
      }
    }
  }

  bool get _canContinue => switch (_step) {
    1 => _quote != null && _quoteError == null && !_quoting,
    2 => _areaId != null && _address.text.trim().length >= 3,
    3 => _time != null && !_loadingSlots && _slotsError == null,
    4 =>
      !_submitting &&
          !_quoting &&
          _quote != null &&
          _quoteError == null &&
          _time != null,
    _ => false,
  };
  void _goTo(int step) {
    FocusManager.instance.primaryFocus?.unfocus();
    setState(() => _step = step);
    if (_scroll.hasClients) _scroll.jumpTo(0);
  }

  Future<void> _next() async {
    if (_submitting || !_canContinue) return;
    if (_step < 4) {
      _goTo(_step + 1);
      if (_step == 3) _loadSlots();
      return;
    }
    setState(() => _submitting = true);
    try {
      final body = {
        ..._quoteRequest,
        'area_id': _areaId,
        'address_line': _address.text.trim(),
        'landmark': _landmark.text.trim().isEmpty
            ? null
            : _landmark.text.trim(),
        'special_instructions': _instructions.text.trim().isEmpty
            ? null
            : _instructions.text.trim(),
        'scheduled_date': DateFormat('yyyy-MM-dd').format(_date),
        'scheduled_start_time': _time,
        'payment_method': 'CASH',
      };
      final signature = jsonEncode(body);
      if (_submissionBody != signature) {
        _submissionBody = signature;
        final random = Random.secure();
        _submissionKey = base64Url.encode(
          List.generate(18, (_) => random.nextInt(256)),
        );
      }
      final booking = await _repo.createBooking(
        body,
        requestKey: _submissionKey,
      );
      if (mounted) Navigator.of(context).pop(booking);
    } catch (e) {
      if (mounted) {
        showError(context, e);
        // Keep the same request key for server-side idempotency on retry.
        if (e is ApiException &&
            (e.code.contains('TIME') ||
                e.code.contains('PROVIDER') ||
                e.code.contains('SLOT'))) {
          _goTo(3);
          _loadSlots();
        }
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final titles = [
      l.stepService,
      l.stepDetails,
      l.stepLocation,
      l.stepSchedule,
      l.stepReview,
    ];
    final progressStyle = Theme.of(context).textTheme.bodySmall!.copyWith(
      fontWeight: FontWeight.w600,
      color: Brand.green700,
    );
    final progress = '${_step + 1}/5 · ${titles[_step]}';
    final painter = TextPainter(
      text: TextSpan(text: progress, style: progressStyle),
      textDirection: Directionality.of(context),
      textScaler: MediaQuery.textScalerOf(context),
    )..layout(maxWidth: MediaQuery.sizeOf(context).width - 32);
    final progressHeight = painter.height + 20;
    painter.dispose();
    return PopScope(
      canPop: _step == 0 && !_submitting,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop && !_submitting && _step > 0) _goTo(_step - 1);
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(l.bookCleaning),
          leading: IconButton(
            icon: Icon(_step > 0 ? Icons.arrow_back : Icons.close),
            tooltip: l.back,
            onPressed: _submitting
                ? null
                : () => _step > 0
                      ? _goTo(_step - 1)
                      : Navigator.of(context).pop(),
          ),
          bottom: PreferredSize(
            preferredSize: Size.fromHeight(progressHeight),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      for (var i = 0; i < 5; i++)
                        Expanded(
                          child: Container(
                            height: 4,
                            margin: const EdgeInsets.symmetric(horizontal: 2),
                            decoration: BoxDecoration(
                              color: i <= _step ? Brand.green600 : Brand.line,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(progress, style: progressStyle),
                ],
              ),
            ),
          ),
        ),
        body: _body(l),
        bottomNavigationBar: _step == 0 || _service == null
            ? null
            : _bottomBar(l),
      ),
    );
  }

  Widget _body(AppLocalizations l) {
    if (_loadError != null) {
      return ErrorRetry(error: _loadError!, onRetry: _loadCatalogue);
    }
    if (_services == null) return LoadingState(l.loadingServices);
    final locale = Localizations.localeOf(context).languageCode;
    return ListView(
      controller: _scroll,
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
      children: switch (_step) {
        0 => [
          Text(l.chooseService, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 14),
          for (final s in _services!) ...[
            ServiceRow(
              service: s,
              onTap: () async {
                final choose = await showServiceSheet(context, s);
                if (choose == true && mounted) _chooseService(s);
              },
            ),
            const Divider(),
          ],
        ],
        1 => _detailsStep(l, locale),
        2 => _locationStep(l),
        3 => _scheduleStep(l),
        _ => _reviewStep(l, locale),
      },
    );
  }

  List<Widget> _detailsStep(AppLocalizations l, String locale) {
    final s = _service!;
    Widget choices(
      String title,
      List<ServiceOption> options,
      String? selected,
      ValueChanged<String> onSelect,
    ) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final o in options)
              ChoiceChip(
                label: Text(
                  o.price > 0
                      ? '${o.name(locale)}  +${formatMoney(o.price)}'
                      : o.name(locale),
                ),
                selected: selected == o.id,
                onSelected: (_) {
                  onSelect(o.id);
                  _requestQuote();
                },
              ),
          ],
        ),
        const SizedBox(height: 20),
      ],
    );
    return [
      Row(
        children: [
          ServiceBadge(s.icon, size: 40),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              s.name(locale),
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
        ],
      ),
      TextButton.icon(
        onPressed: () => showServiceSheet(context, s, canSelect: false),
        icon: const Icon(Icons.info_outline, size: 18),
        label: Text(l.serviceDetails),
      ),
      const SizedBox(height: 16),
      if (s.group('PROPERTY_TYPE').isNotEmpty)
        choices(
          l.propertyType,
          s.group('PROPERTY_TYPE'),
          _propertyTypeId,
          (id) => setState(() => _propertyTypeId = id),
        ),
      if (s.group('SIZE').isNotEmpty)
        choices(
          l.size,
          s.group('SIZE'),
          _sizeId,
          (id) => setState(() => _sizeId = id),
        ),
      if (s.usesRooms) ...[
        Counter(
          label: l.bedrooms,
          value: _bedrooms,
          max: s.maxRooms,
          onChanged: (v) {
            setState(() => _bedrooms = v);
            _requestQuote();
          },
        ),
        const SizedBox(height: 12),
        Counter(
          label: l.bathrooms,
          value: _bathrooms,
          min: 1,
          max: s.maxRooms,
          onChanged: (v) {
            setState(() => _bathrooms = v);
            _requestQuote();
          },
        ),
        const SizedBox(height: 20),
      ],
      if (s.group('ADDON').isNotEmpty) ...[
        Text(l.addons, style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: [
              for (final o in s.group('ADDON'))
                o.maxQuantity > 1
                    ? Padding(
                        padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
                        child: Counter(
                          label: '${o.name(locale)}\n+${formatMoney(o.price)}',
                          value: _addons[o.id] ?? 0,
                          max: o.maxQuantity,
                          onChanged: (v) {
                            setState(() => _addons[o.id] = v);
                            _requestQuote();
                          },
                        ),
                      )
                    : CheckboxListTile(
                        value: (_addons[o.id] ?? 0) > 0,
                        activeColor: Brand.green700,
                        title: Text(o.name(locale)),
                        subtitle: Text('+${formatMoney(o.price)}'),
                        onChanged: (v) {
                          setState(() => _addons[o.id] = v == true ? 1 : 0);
                          _requestQuote();
                        },
                      ),
            ],
          ),
        ),
      ],
      if (_quoteError != null) ...[
        const SizedBox(height: 12),
        ErrorRetry(
          error: _quoteError!,
          onRetry: () => _requestQuote(immediate: true),
        ),
      ],
    ];
  }

  List<Widget> _locationStep(AppLocalizations l) => [
    Text(l.locationTitle, style: Theme.of(context).textTheme.titleLarge),
    const SizedBox(height: 8),
    Text(l.locationHint, style: const TextStyle(color: Brand.ink3)),
    const SizedBox(height: 24),
    DropdownButtonFormField<String>(
      initialValue: _areaId,
      isExpanded: true,
      decoration: InputDecoration(labelText: l.area),
      hint: Text(l.chooseArea),
      items: [
        for (final a in _areas!)
          DropdownMenuItem(
            value: a.id,
            child: Text('${a.name}, ${a.cityName}'),
          ),
      ],
      onChanged: (v) => setState(() {
        _areaId = v;
        _time = null;
      }),
    ),
    const SizedBox(height: 14),
    TextField(
      key: const ValueKey('booking-address'),
      controller: _address,
      decoration: InputDecoration(
        labelText: l.address,
        hintText: l.addressHint,
        helperText: l.addressValidation,
        helperMaxLines: 2,
      ),
      textInputAction: TextInputAction.next,
      textCapitalization: TextCapitalization.sentences,
      onChanged: (_) => setState(() {}),
    ),
    const SizedBox(height: 14),
    TextField(
      controller: _landmark,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(labelText: l.landmark),
    ),
    const SizedBox(height: 14),
    TextField(
      controller: _instructions,
      minLines: 1,
      maxLines: 3,
      textInputAction: TextInputAction.done,
      decoration: InputDecoration(
        labelText: l.instructions,
        hintText: l.instructionsHint,
      ),
    ),
  ];
  List<Widget> _scheduleStep(AppLocalizations l) {
    final today = DateTime.now();
    final days = [
      for (var i = 0; i < 14; i++)
        DateTime(today.year, today.month, today.day + i),
    ];
    final lang = Localizations.localeOf(context).languageCode;
    return [
      Text(l.chooseDate, style: const TextStyle(fontWeight: FontWeight.w600)),
      const SizedBox(height: 10),
      SizedBox(
        height: 104 * MediaQuery.textScalerOf(context).scale(1).clamp(1, 3),
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: days.length,
          separatorBuilder: (_, _) => const SizedBox(width: 8),
          itemBuilder: (_, i) {
            final d = days[i];
            final selected = DateUtils.isSameDay(d, _date);
            return Semantics(
              key: ValueKey(
                'booking-date-${DateFormat('yyyy-MM-dd').format(d)}',
              ),
              button: true,
              selected: selected,
              label: DateFormat.yMMMEd(lang).format(d),
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () {
                  setState(() {
                    _date = d;
                    _time = null;
                  });
                  _loadSlots();
                },
                child: Container(
                  width:
                      66 *
                      MediaQuery.textScalerOf(context).scale(1).clamp(1, 3),
                  decoration: BoxDecoration(
                    color: selected ? Brand.green50 : Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: selected ? Brand.green600 : Brand.line,
                      width: selected ? 1.5 : 1,
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        DateFormat.E(lang).format(d),
                        style: const TextStyle(fontSize: 12, color: Brand.ink3),
                      ),
                      Text(
                        '${d.day}',
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        DateFormat.MMM(lang).format(d),
                        style: const TextStyle(fontSize: 12, color: Brand.ink3),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
      const SizedBox(height: 22),
      Text(l.chooseTime, style: const TextStyle(fontWeight: FontWeight.w600)),
      const SizedBox(height: 10),
      if (_loadingSlots) LoadingState(l.loadingSlots),
      if (_slotsError != null)
        ErrorRetry(error: _slotsError!, onRetry: _loadSlots),
      if (_slots != null && !_slots!.any((s) => s.available))
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Brand.amber50,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(l.noSlots, style: const TextStyle(color: Brand.amber700)),
        ),
      if (_slots != null)
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final slot in _slots!)
              _SlotTile(
                slot: slot,
                selected: _time == slot.start,
                unavailableLabel: l.unavailable,
                onTap: slot.available
                    ? () => setState(() => _time = slot.start)
                    : null,
              ),
          ],
        ),
    ];
  }

  List<Widget> _reviewStep(AppLocalizations l, String locale) {
    final area = _areas!.where((a) => a.id == _areaId).firstOrNull;
    final q = _quote!;
    return [
      Text(l.reviewBooking, style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 16),
      SectionCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                ServiceBadge(_service!.icon, size: 40),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    _service!.name(locale),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            SectionHeader(
              l.property,
              action: TextButton(
                onPressed: () => _goTo(1),
                child: Text(l.edit),
              ),
            ),
            Text(
              [
                if (_propertyTypeId != null)
                  _service!.options
                      .firstWhere((o) => o.id == _propertyTypeId)
                      .name(locale),
                if (_service!.usesRooms) l.rooms(_bedrooms, _bathrooms),
                if (_sizeId != null)
                  _service!.options
                      .firstWhere((o) => o.id == _sizeId)
                      .name(locale),
              ].join(' · '),
            ),
            SectionHeader(
              l.stepSchedule,
              action: TextButton(
                onPressed: () => _goTo(3),
                child: Text(l.edit),
              ),
            ),
            _kv(
              l.when,
              '${formatDate(context, _date)} · $_time–${addMinutes(_time!, q.durationMinutes)}',
            ),
            SectionHeader(
              l.stepLocation,
              action: TextButton(
                onPressed: () => _goTo(2),
                child: Text(l.edit),
              ),
            ),
            _kv(l.where, '${_address.text.trim()}, ${area?.name ?? ''}'),
            _kv(
              l.estimatedDuration,
              formatDuration(context, q.durationMinutes),
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: l.priceBreakdown,
        child: PriceLines(
          lines: [
            for (final line in q.lines)
              (
                label: line.label(locale),
                quantity: line.quantity,
                amount: line.amount,
              ),
          ],
          total: q.total,
          currency: q.currency,
        ),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: l.paymentMethod,
        child: Column(
          children: [
            _PaymentOption(
              icon: Icons.payments_outlined,
              title: l.cash,
              subtitle: l.cashHint,
              selected: true,
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      Row(
        children: [
          const Icon(
            Icons.cleaning_services_outlined,
            color: Brand.green700,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              l.materialsIncluded,
              style: const TextStyle(color: Brand.green700),
            ),
          ),
        ],
      ),
    ];
  }

  Widget _kv(String k, String v) => SummaryRow(k, v);
  Widget _bottomBar(AppLocalizations l) {
    final total = _quote == null
        ? '—'
        : formatMoney(_quote!.total, _quote!.currency);
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Brand.line)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Expanded(
                  child: Text(
                    _quoting ? l.updatingPrice : l.total,
                    style: const TextStyle(color: Brand.ink3),
                  ),
                ),
                const SizedBox(width: 8),
                // Flexible keeps large accessibility font sizes from overflowing narrow phones.
                Flexible(
                  child: Align(
                    alignment: AlignmentDirectional.centerEnd,
                    child: Text(
                      total,
                      textAlign: TextAlign.end,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            FilledButton(
              key: const ValueKey('booking-next'),
              onPressed: _canContinue ? _next : null,
              child: _submitting
                  ? Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        const SizedBox(width: 8),
                        Flexible(child: Text(l.confirmingBooking)),
                      ],
                    )
                  : Text(
                      _step < 4 ? l.continueLabel : l.confirmBookingLabel,
                      textAlign: TextAlign.center,
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SlotTile extends StatelessWidget {
  final Slot slot;
  final bool selected;
  final String unavailableLabel;
  final VoidCallback? onTap;
  const _SlotTile({
    required this.slot,
    required this.selected,
    required this.unavailableLabel,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    selected: selected,
    enabled: slot.available,
    child: InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Opacity(
        opacity: slot.available ? 1 : .45,
        child: Container(
          constraints: const BoxConstraints(minHeight: 72, minWidth: 88),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: selected ? Brand.green50 : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: selected ? Brand.green600 : Brand.line,
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (selected)
                    const Padding(
                      padding: EdgeInsets.only(right: 4),
                      child: Icon(Icons.check, size: 16, color: Brand.green700),
                    ),
                  Text(
                    slot.start,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 16,
                    ),
                  ),
                ],
              ),
              Text(
                slot.available ? '– ${slot.end}' : unavailableLabel,
                style: const TextStyle(fontSize: 11, color: Brand.ink3),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _PaymentOption extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool selected;
  const _PaymentOption({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.selected,
  });

  @override
  Widget build(BuildContext context) => Opacity(
    opacity: selected ? 1 : .55,
    child: Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: selected ? Brand.green50 : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: selected ? Brand.green600 : Brand.line,
          width: selected ? 1.5 : 1,
        ),
      ),
      child: Row(
        children: [
          Icon(icon, color: selected ? Brand.green700 : Brand.ink3),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                Text(
                  subtitle,
                  style: const TextStyle(fontSize: 12, color: Brand.ink3),
                ),
              ],
            ),
          ),
          if (selected) const Icon(Icons.check_circle, color: Brand.green600),
        ],
      ),
    ),
  );
}
