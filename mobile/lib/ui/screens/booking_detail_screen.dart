import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/repository.dart';
import '../../l10n/app_localizations.dart';
import '../../models/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/booking_widgets.dart';
import '../widgets/service_widgets.dart';

class BookingDetailScreen extends StatefulWidget {
  final String bookingId;
  final bool justCreated;
  final ValueChanged<BookingDetail>? onBookAgain;
  const BookingDetailScreen({
    super.key,
    required this.bookingId,
    this.justCreated = false,
    this.onBookAgain,
  });

  @override
  State<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends State<BookingDetailScreen>
    with WidgetsBindingObserver {
  BookingDetail? _booking;
  Object? _error;
  bool _busy = false;
  final _refresh = RefreshGate();
  late bool _showSuccess;
  Timer? _poll;
  int _rating = 0;
  final _comment = TextEditingController();

  Repository get _repo => context.read<Repository>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _showSuccess = widget.justCreated;
    _load();
    _poll = Timer.periodic(const Duration(seconds: 15), (_) {
      if (_booking != null &&
          liveStatuses.contains(_booking!.status) &&
          ModalRoute.of(context)?.isCurrent == true &&
          WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed) {
        _load();
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _poll?.cancel();
    _comment.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _load();
  }

  Future<void> _load() => _refresh.run(() async {
    try {
      final b = await _repo.booking(widget.bookingId);
      if (mounted) {
        setState(() {
          _booking = b;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  });

  Future<void> _run(Future<void> Function() action, {String? success}) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
      await _load();
      if (success != null && mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(success)));
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancel() async {
    final l = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l.cancelBooking),
        content: Text(l.cancelConfirm),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(l.keep),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: Brand.red600),
            child: Text(l.cancelBooking),
          ),
        ],
      ),
    );
    if (ok == true) await _run(() => _repo.cancel(widget.bookingId));
  }

  Future<void> _reportIssue() async {
    final l = AppLocalizations.of(context);
    final result = await showModalBottomSheet<(String, String)>(
      context: context,
      useSafeArea: true,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => const _IssueSheet(),
    );
    if (result != null) {
      await _run(
        () => _repo.reportIssue(widget.bookingId, result.$1, result.$2),
        success: l.issueSent,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final b = _booking;
    return Scaffold(
      appBar: AppBar(
        // The success screen carries its own heading; the reference is the title elsewhere.
        title: _showSuccess ? null : Text(b?.reference ?? l.bookings),
        actions: [
          if (!_showSuccess)
            IconButton(
              tooltip: l.refreshBooking,
              onPressed: _busy ? null : _load,
              icon: const Icon(Icons.refresh),
            ),
          IconButton(
            tooltip: l.support,
            onPressed: () => showSupportSheet(context),
            icon: const Icon(Icons.help_outline),
          ),
        ],
      ),
      body: b == null
          ? (_error != null
                ? ErrorRetry(error: _error!, onRetry: _load)
                : LoadingState(l.loadingBooking))
          : _showSuccess
          ? BookingSuccess(
              booking: b,
              onTrack: () => setState(() => _showSuccess = false),
              onHome: () => Navigator.of(context).pop(),
            )
          : RefreshIndicator(onRefresh: _load, child: _content(l, b)),
    );
  }

  Widget _content(AppLocalizations l, BookingDetail b) {
    final locale = Localizations.localeOf(context).languageCode;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        if (_error != null) ...[
          Text(l.refreshFailed, style: const TextStyle(color: Brand.amber700)),
          TextButton(onPressed: _load, child: Text(l.retry)),
          const SizedBox(height: 12),
        ],
        BookingStatusPanel(b),
        const SizedBox(height: 24),
        Row(
          children: [
            ServiceBadge(b.serviceIcon),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    b.serviceName(locale),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  Text(
                    '${formatDate(context, b.date)} · ${b.startTime}–${addMinutes(b.startTime, b.durationMinutes)}',
                    style: const TextStyle(color: Brand.ink3),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),

        if (b.can('CONFIRM_COMPLETION')) ...[
          SectionCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              // The status panel above already asks the question; this card only holds the answers.
              children: [
                FilledButton.icon(
                  onPressed: _busy
                      ? null
                      : () => _run(() => _repo.confirmCompletion(b.id)),
                  icon: const Icon(Icons.check_circle_outline),
                  label: Text(l.confirmCompletion),
                ),
                if (b.can('REPORT_ISSUE')) ...[
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _reportIssue,
                    icon: const Icon(Icons.report_outlined),
                    label: Text(l.reportIssue),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],
        if (b.can('REVIEW')) ...[
          SectionCard(title: l.rateTitle, child: _reviewForm(l, b)),
          const SizedBox(height: 12),
        ],
        if (b.review != null) ...[
          SectionCard(
            title: l.yourReview,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _stars((b.review!['rating'] as num).toInt()),
                if ((b.review!['comment'] as String?)?.isNotEmpty ?? false) ...[
                  const SizedBox(height: 6),
                  Text(b.review!['comment']),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],

        // Who is coming matters more than the step history, so the cleaner comes first.
        if (b.provider != null) ...[
          SectionCard(
            title: l.yourCleaner,
            child: ProviderSummary(b.provider!),
          ),
          const SizedBox(height: 12),
        ],
        // While the booking is live the timeline is the point of this screen: show it open.
        ExpansionTile(
          key: PageStorageKey('timeline-${b.id}'),
          initiallyExpanded: liveStatuses.contains(b.status),
          title: Text(l.progress),
          tilePadding: EdgeInsets.zero,
          childrenPadding: const EdgeInsets.only(bottom: 16),
          children: [BookingTimeline(b)],
        ),
        const SizedBox(height: 12),
        SectionCard(
          title: l.details,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                b.addressLine ?? '',
                style: const TextStyle(fontWeight: FontWeight.w500),
              ),
              if (b.landmark != null)
                Text(b.landmark!, style: const TextStyle(color: Brand.ink3)),
              Text(b.areaName, style: const TextStyle(color: Brand.ink3)),
              if (b.bathrooms > 0) ...[
                const SizedBox(height: 8),
                Text(l.rooms(b.bedrooms, b.bathrooms)),
              ],
            ],
          ),
        ),
        const SizedBox(height: 12),
        SectionCard(
          title: l.priceBreakdown,
          child: Column(
            children: [
              PriceLines(
                lines: [
                  for (final line in b.priceItems)
                    (
                      label: line.label(locale),
                      quantity: line.quantity,
                      amount: line.amount,
                    ),
                ],
                total: b.total,
                currency: b.currency,
              ),
              if (b.payment != null) ...[
                const SizedBox(height: 12),
                SummaryRow(
                  l.paymentAfter,
                  paymentLabel(l, b.payment!['status']),
                ),
              ],
            ],
          ),
        ),
        if (b.can('REPORT_ISSUE') && !b.can('CONFIRM_COMPLETION')) ...[
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: _busy ? null : _reportIssue,
            icon: const Icon(Icons.report_outlined),
            label: Text(l.reportIssue),
          ),
        ],
        if (b.status == 'CLOSED' && widget.onBookAgain != null) ...[
          const SizedBox(height: 16),
          OutlinedButton(
            onPressed: () => widget.onBookAgain!(b),
            child: Text(l.bookAgain),
          ),
        ],
        const SizedBox(height: 16),
        TextButton.icon(
          onPressed: () => showSupportSheet(context),
          icon: const Icon(Icons.help_outline),
          label: Text(l.contactSupport),
        ),
        if (b.can('CANCEL')) ...[
          const SizedBox(height: 20),
          OutlinedButton(
            onPressed: _busy ? null : _cancel,
            style: OutlinedButton.styleFrom(
              foregroundColor: Brand.red600,
              side: const BorderSide(color: Color(0xFFF0C9C3)),
            ),
            child: Text(l.cancelBooking),
          ),
        ],
      ],
    );
  }

  Widget _stars(int value, {ValueChanged<int>? onTap}) => Wrap(
    children: [
      for (var i = 1; i <= 5; i++)
        onTap == null
            ? Icon(
                i <= value ? Icons.star : Icons.star_outline,
                color: const Color(0xFF98651A),
                size: 24,
              )
            : Semantics(
                selected: i == value,
                child: IconButton(
                  tooltip: AppLocalizations.of(context).ratingLabel(i),
                  onPressed: _busy ? null : () => onTap(i),
                  icon: Icon(i <= value ? Icons.star : Icons.star_outline),
                  color: const Color(0xFF98651A),
                  iconSize: 32,
                ),
              ),
    ],
  );

  Widget _reviewForm(AppLocalizations l, BookingDetail b) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      _stars(_rating, onTap: (v) => setState(() => _rating = v)),
      const SizedBox(height: 12),
      TextField(
        controller: _comment,
        maxLines: 3,
        decoration: InputDecoration(labelText: l.rateComment),
      ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _rating == 0 || _busy
            ? null
            : () => _run(
                () => _repo.review(
                  b.id,
                  _rating,
                  _comment.text.trim().isEmpty ? null : _comment.text.trim(),
                ),
                success: l.thanksReview,
              ),
        child: Text(l.submitReview),
      ),
    ],
  );
}

class _IssueSheet extends StatefulWidget {
  const _IssueSheet();
  @override
  State<_IssueSheet> createState() => _IssueSheetState();
}

class _IssueSheetState extends State<_IssueSheet> {
  final _description = TextEditingController();
  String _category = 'QUALITY';
  @override
  void dispose() {
    _description.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final categories = [
      ('QUALITY', l.issueQuality),
      ('LATE_OR_NO_SHOW', l.issueLate),
      ('DAMAGE', l.issueDamage),
      ('CONDUCT', l.issueConduct),
      ('PAYMENT', l.issuePayment),
      ('OTHER', l.issueOther),
    ];
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        0,
        20,
        20 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(l.reportIssue, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 20),
            DropdownButtonFormField<String>(
              initialValue: _category,
              isExpanded: true,
              decoration: InputDecoration(labelText: l.issueCategory),
              items: [
                for (final c in categories)
                  DropdownMenuItem(value: c.$1, child: Text(c.$2)),
              ],
              onChanged: (v) => setState(() => _category = v ?? _category),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _description,
              minLines: 3,
              maxLines: 5,
              maxLength: 2000,
              decoration: InputDecoration(
                labelText: l.issueDescription,
                helperText: l.issueDescriptionHint,
                helperMaxLines: 3,
              ),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _description.text.trim().length < 10
                  ? null
                  : () => Navigator.pop(context, (
                      _category,
                      _description.text.trim(),
                    )),
              child: Text(l.sendIssue),
            ),
          ],
        ),
      ),
    );
  }
}
