import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../models/models.dart';
import '../theme.dart';
import 'common.dart';
import 'editorial_photo.dart';

class HomeHero extends StatelessWidget {
  const HomeHero({super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: EditorialPhoto(
        asset: EditorialImages.home,
        label: l.peaceHomePhotoAlt,
        height:
            ((MediaQuery.sizeOf(context).height -
                        MediaQuery.paddingOf(context).vertical -
                        80) *
                    .35)
                .clamp(180, 320),
        alignment: const Alignment(-.25, 0),
      ),
    );
  }
}

class BookingQuickStart extends StatelessWidget {
  final VoidCallback onBook;
  const BookingQuickStart({super.key, required this.onBook});
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          l.homeEyebrow,
          style: const TextStyle(
            fontSize: 11,
            letterSpacing: 1.3,
            fontWeight: FontWeight.w600,
            color: Brand.green700,
          ),
        ),
        const SizedBox(height: 10),
        Text(
          l.homeHeadline,
          style: TextStyle(
            fontSize: MediaQuery.sizeOf(context).width < 360 ? 28 : 34,
            height: 1.08,
            letterSpacing: -1,
            fontWeight: FontWeight.w600,
            color: Brand.green900,
          ),
        ),
        const SizedBox(height: 12),
        Text(l.homePromise, style: const TextStyle(color: Brand.ink2)),
        const SizedBox(height: 20),
        FilledButton(
          key: const ValueKey('home-book'),
          onPressed: onBook,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Expanded(
                child: Text(l.bookCleaning, textAlign: TextAlign.center),
              ),
              const Icon(Icons.arrow_forward, size: 20),
            ],
          ),
        ),
      ],
    );
  }
}

class TrustStrip extends StatelessWidget {
  const TrustStrip({super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 20),
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: Brand.line),
          bottom: BorderSide(color: Brand.line),
        ),
      ),
      child: Wrap(
        spacing: 20,
        runSpacing: 12,
        children: [
          for (final item in [
            (Icons.verified_user_outlined, l.verifiedProfessionals),
            (Icons.cleaning_services_outlined, l.equipmentIncluded),
            (Icons.receipt_long_outlined, l.transparentPricing),
          ])
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(item.$1, size: 18, color: Brand.green700),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    item.$2,
                    style: const TextStyle(fontSize: 12, color: Brand.ink2),
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }
}

class ServicePreview extends StatelessWidget {
  final Service service;
  final VoidCallback onTap;
  const ServicePreview({super.key, required this.service, required this.onTap});
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final photo = EditorialImages.services[service.slug];
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 88,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: photo == null
                    ? ServiceBadge(service.icon, size: 88)
                    : EditorialPhoto(
                        asset: photo,
                        label: l.servicePhotoAlt,
                        height: 100,
                        decodeWidth: 264,
                      ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    service.name(lang),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    service.summary(lang),
                    style: const TextStyle(color: Brand.ink3),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    l.fromPrice(formatMoney(service.basePrice)),
                    style: const TextStyle(
                      color: Brand.green700,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_outward, size: 18, color: Brand.ink3),
          ],
        ),
      ),
    );
  }
}
