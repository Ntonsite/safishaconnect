import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../l10n/app_localizations.dart';
import '../../models/models.dart';
import '../theme.dart';
import 'common.dart';

(String, String) bookingMessage(AppLocalizations l, String status) =>
    switch (status) {
      'FINDING_PROVIDER' ||
      'REASSIGNMENT_REQUIRED' => (l.findingTitle, l.awaitingCleaner),
      'PROVIDER_ASSIGNED' => (l.assignedTitle, l.assignedBody),
      'PROVIDER_EN_ROUTE' => (l.enRouteTitle, l.enRouteBody),
      'PROVIDER_ARRIVED' => (l.arrivedTitle, l.arrivedBody),
      'SERVICE_IN_PROGRESS' => (l.inProgressTitle, l.inProgressBody),
      'COMPLETED_BY_PROVIDER' => (l.completedTitle, l.confirmCompletionBody),
      'CUSTOMER_CONFIRMED' || 'CLOSED' => (l.completedTitle, l.closedBody),
      'CANCELLED' => (l.statusCANCELLED, l.cancelledBody),
      'DISPUTED' => (l.statusDISPUTED, l.disputedBody),
      _ => (statusLabel(l, status), l.findingProvider),
    };

class BookingStatusPanel extends StatelessWidget {
  final BookingDetail booking;
  const BookingStatusPanel(this.booking, {super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final (title, body) = bookingMessage(l, booking.status);
    return Semantics(
      liveRegion: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          StatusChip(booking.status),
          const SizedBox(height: 12),
          Text(title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text(body, style: const TextStyle(color: Brand.ink2)),
        ],
      ),
    );
  }
}

class BookingTimeline extends StatelessWidget {
  final BookingDetail booking;
  const BookingTimeline(this.booking, {super.key});
  static const journey = [
    'CONFIRMED',
    'FINDING_PROVIDER',
    'PROVIDER_ASSIGNED',
    'PROVIDER_EN_ROUTE',
    'PROVIDER_ARRIVED',
    'SERVICE_IN_PROGRESS',
    'COMPLETED_BY_PROVIDER',
    'CUSTOMER_CONFIRMED',
    'CLOSED',
  ];
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    if (booking.status == 'CANCELLED') return Text(l.statusCANCELLED);
    final status = booking.status == 'REASSIGNMENT_REQUIRED'
        ? 'FINDING_PROVIDER'
        : booking.status == 'DISPUTED'
        ? booking.history.reversed
                  .where((h) => journey.contains(h.toStatus))
                  .firstOrNull
                  ?.toStatus ??
              'FINDING_PROVIDER'
        : booking.status;
    final position = journey.indexOf(status);
    return Column(
      children: [
        for (final (i, step) in journey.indexed)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: i < position || booking.status == 'CLOSED'
                        ? Brand.green700
                        : Colors.white,
                    border: Border.all(
                      color: i <= position ? Brand.green700 : Brand.line,
                      width: 2,
                    ),
                  ),
                  child: i < position || booking.status == 'CLOSED'
                      ? const Icon(Icons.check, size: 14, color: Colors.white)
                      : i == position
                      ? const Icon(
                          Icons.circle,
                          size: 10,
                          color: Brand.green700,
                        )
                      : null,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        i == position && booking.status != 'DISPUTED'
                            ? statusLabel(l, booking.status)
                            : statusLabel(l, step),
                        style: TextStyle(
                          fontWeight: i == position
                              ? FontWeight.w600
                              : FontWeight.w400,
                          color: i <= position ? Brand.ink : Brand.ink3,
                        ),
                      ),
                      if (booking.history.any((h) => h.toStatus == step))
                        Text(
                          DateFormat(
                            'd MMM, HH:mm',
                            Localizations.localeOf(context).languageCode,
                          ).format(
                            booking.history
                                .lastWhere((h) => h.toStatus == step)
                                .at,
                          ),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class ProviderSummary extends StatelessWidget {
  final Map<String, dynamic> provider;
  const ProviderSummary(this.provider, {super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final name = provider['display_name'] as String? ?? '';
    final count = provider['rating_count'] as int? ?? 0;
    final rating = num.tryParse('${provider['rating_average']}') ?? 0;
    final phone = provider['phone'] as String?;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              radius: 22,
              backgroundColor: Brand.green100,
              child: Text(
                name
                    .split(' ')
                    .where((s) => s.isNotEmpty)
                    .take(2)
                    .map((s) => s[0])
                    .join(),
                style: const TextStyle(
                  color: Brand.green900,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 12,
                    runSpacing: 6,
                    children: [
                      Text(
                        l.verified,
                        style: const TextStyle(color: Brand.green700),
                      ),
                      if (count > 0)
                        Text(
                          '★ ${rating.toStringAsFixed(1)} ($count)',
                          style: const TextStyle(color: Brand.ink3),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
        if (phone != null && phone.isNotEmpty) ...[
          const SizedBox(height: 12),
          SelectableText(formatPhone(phone)),
          TextButton.icon(
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: phone));
              if (context.mounted) {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text(l.numberCopied)));
              }
            },
            icon: const Icon(Icons.copy_outlined, size: 18),
            label: Text(l.copyNumber),
          ),
        ],
      ],
    );
  }
}

class BookingSuccess extends StatelessWidget {
  final BookingDetail booking;
  final VoidCallback onTrack;
  final VoidCallback onHome;
  const BookingSuccess({
    super.key,
    required this.booking,
    required this.onTrack,
    required this.onHome,
  });
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 32, 24, 32),
      children: [
        const Align(
          alignment: Alignment.centerLeft,
          child: Icon(
            Icons.check_circle_outline,
            color: Brand.green700,
            size: 48,
          ),
        ),
        const SizedBox(height: 20),
        Text(
          l.bookingConfirmed,
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 12),
        Text(
          '${l.bookingReference}: ${booking.reference}',
          style: const TextStyle(color: Brand.ink3),
        ),
        const SizedBox(height: 28),
        Text(
          booking.serviceName(lang),
          style: Theme.of(context).textTheme.titleLarge,
        ),
        SummaryRow(
          l.when,
          '${formatDate(context, booking.date)} · ${booking.startTime}',
        ),
        SummaryRow(l.where, booking.areaName),
        SummaryRow(l.total, formatMoney(booking.total, booking.currency)),
        const SizedBox(height: 16),
        const Divider(),
        const SizedBox(height: 20),
        Text(l.findingProvider, style: const TextStyle(color: Brand.ink2)),
        const SizedBox(height: 24),
        FilledButton(
          key: const ValueKey('track-booking'),
          onPressed: onTrack,
          child: Text(l.trackBooking),
        ),
        const SizedBox(height: 8),
        TextButton(onPressed: onHome, child: Text(l.backHome)),
      ],
    );
  }
}
