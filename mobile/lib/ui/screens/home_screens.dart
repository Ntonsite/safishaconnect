import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/repository.dart';
import '../../l10n/app_localizations.dart';
import '../../models/models.dart';
import '../../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/editorial_photo.dart';
import '../widgets/home_editorial.dart';
import '../widgets/service_widgets.dart';
import 'booking_detail_screen.dart';
import 'booking_flow_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;
  final _visited = <int>{0};
  final _homeKey = GlobalKey<_HomeTabState>();
  final _bookingsKey = GlobalKey<_BookingsTabState>();
  bool _openingBooking = false;
  bool _loadingRepeat = false;

  Future<void> _repeat(BookingSummary booking) async {
    if (_loadingRepeat || _openingBooking) return;
    _loadingRepeat = true;
    try {
      final detail = await context.read<Repository>().booking(booking.id);
      if (mounted) await _book(repeat: detail);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      _loadingRepeat = false;
    }
  }

  Future<void> _book({Service? service, BookingDetail? repeat}) async {
    if (_openingBooking) return;
    _openingBooking = true;
    try {
      final created = await Navigator.of(context).push<BookingDetail>(
        MaterialPageRoute(
          builder: (_) =>
              BookingFlowScreen(initialService: service, repeatBooking: repeat),
        ),
      );
      _openingBooking = false;
      if (created != null && mounted) {
        await Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => BookingDetailScreen(
              bookingId: created.id,
              justCreated: true,
              onBookAgain: (b) => _book(repeat: b),
            ),
          ),
        );
      }
      if (mounted) {
        _homeKey.currentState?.reload(showActive: created != null);
        _bookingsKey.currentState?.reload();
      }
    } finally {
      _openingBooking = false;
    }
  }

  Future<void> _detail(BookingSummary booking) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => BookingDetailScreen(
          bookingId: booking.id,
          onBookAgain: (b) => _book(repeat: b),
        ),
      ),
    );
    if (mounted) {
      _homeKey.currentState?.reload();
      _bookingsKey.currentState?.reload();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: IndexedStack(
          index: _tab,
          children: [
            _HomeTab(
              key: _homeKey,
              onBook: () => _book(),
              onService: (s) => _book(service: s),
              onDetail: _detail,
              onRepeat: _repeat,
            ),
            _visited.contains(1)
                ? _BookingsTab(
                    key: _bookingsKey,
                    onBook: () => _book(),
                    onDetail: _detail,
                  )
                : const SizedBox.shrink(),
            _visited.contains(2)
                ? const _ProfileTab()
                : const SizedBox.shrink(),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) {
          if (_tab == i) return;
          setState(() {
            _tab = i;
            _visited.add(i);
          });
          if (i == 0) _homeKey.currentState?.reload(showActive: true);
          if (i == 1) _bookingsKey.currentState?.reload();
        },
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.home_outlined),
            selectedIcon: const Icon(Icons.home),
            label: l.home,
          ),
          NavigationDestination(
            icon: const Icon(Icons.receipt_long_outlined),
            selectedIcon: const Icon(Icons.receipt_long),
            label: l.bookings,
          ),
          NavigationDestination(
            icon: const Icon(Icons.person_outline),
            selectedIcon: const Icon(Icons.person),
            label: l.profile,
          ),
        ],
      ),
    );
  }
}

class _HomeTab extends StatefulWidget {
  final VoidCallback onBook;
  final ValueChanged<Service> onService;
  final ValueChanged<BookingSummary> onDetail;
  final ValueChanged<BookingSummary> onRepeat;
  const _HomeTab({
    super.key,
    required this.onBook,
    required this.onService,
    required this.onDetail,
    required this.onRepeat,
  });
  @override
  State<_HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<_HomeTab> {
  final _scroll = ScrollController();
  List<Service>? _services;
  List<BookingSummary>? _bookings;
  Object? _error;
  Object? _bookingsError;
  final _refresh = RefreshGate();
  @override
  void initState() {
    super.initState();
    reload();
  }

  Future<void> reload({bool showActive = false}) {
    if (showActive && _scroll.hasClients) _scroll.jumpTo(0);
    return _refresh.run(() async {
      final repo = context.read<Repository>();
      await Future.wait([
        () async {
          try {
            final services = await repo.services();
            if (mounted) {
              setState(() {
                _services = services;
                _error = null;
              });
            }
          } catch (e) {
            if (mounted) setState(() => _error = e);
          }
        }(),
        () async {
          try {
            final bookings = await repo.bookings('all');
            if (mounted) {
              setState(() {
                _bookings = bookings;
                _bookingsError = null;
              });
            }
          } catch (e) {
            if (mounted) setState(() => _bookingsError = e);
          }
        }(),
      ]);
    });
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    precacheImage(EditorialImages.provider(EditorialImages.home), context);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final me = context.watch<AppState>().me;
    final completed =
        (_bookings ?? []).where((b) => b.status == 'CLOSED').toList()
          ..sort((a, b) => b.date.compareTo(a.date));
    final active =
        (_bookings ?? [])
            .where(
              (b) => liveStatuses.contains(b.status) || b.status == 'DISPUTED',
            )
            .toList()
          ..sort(
            (a, b) =>
                '${a.date}${a.startTime}'.compareTo('${b.date}${b.startTime}'),
          );
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(
        controller: _scroll,
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'SafishaCon',
                  style: const TextStyle(
                    color: Brand.green900,
                    fontWeight: FontWeight.w700,
                    fontSize: 19,
                  ),
                ),
              ),
              IconButton(
                tooltip: l.support,
                onPressed: () => showSupportSheet(context),
                icon: const Icon(Icons.help_outline),
              ),
            ],
          ),
          Row(
            children: [
              const Icon(
                Icons.location_on_outlined,
                size: 15,
                color: Brand.ink3,
              ),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  l.serviceCity,
                  style: const TextStyle(fontSize: 12, color: Brand.ink3),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          if (_bookingsError != null)
            ErrorRetry(error: _bookingsError!, onRetry: reload),
          if (_bookings == null && _bookingsError == null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                l.loadingBookings,
                style: const TextStyle(color: Brand.ink3, fontSize: 12),
              ),
            ),
          if (active.isNotEmpty) ...[
            Text(
              l.hello(me?.firstName ?? ''),
              style: const TextStyle(color: Brand.ink3),
            ),
            const SizedBox(height: 8),
            SectionHeader(l.activeBooking),
            const SizedBox(height: 12),
            SectionCard(
              key: const ValueKey('home-active-booking'),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  BookingTile(
                    booking: active.first,
                    onTap: () => widget.onDetail(active.first),
                    padded: false,
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton(
                    onPressed: () => widget.onDetail(active.first),
                    child: Text(l.trackBooking),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
          ],
          const HomeHero(key: ValueKey('home-hero')),
          const SizedBox(height: 24),
          BookingQuickStart(onBook: widget.onBook),
          const SizedBox(height: 24),
          if (active.isEmpty && completed.isNotEmpty) ...[
            SectionHeader(l.lastCleaning),
            BookingTile(
              booking: completed.first,
              onTap: () => widget.onDetail(completed.first),
            ),
            OutlinedButton(
              onPressed: () => widget.onRepeat(completed.first),
              child: Text(l.bookAgain),
            ),
            const SizedBox(height: 24),
          ],
          const TrustStrip(),
          const SizedBox(height: 28),
          if (_error != null) ErrorRetry(error: _error!, onRetry: reload),
          if (_services == null && _error == null)
            LoadingState(l.loadingServices),
          if (_services != null) ...[
            SectionHeader(l.popularServices),
            const SizedBox(height: 4),
            for (final service in _services!) ...[
              ServicePreview(
                service: service,
                onTap: () async {
                  final choose = await showServiceSheet(context, service);
                  if (choose == true && mounted) widget.onService(service);
                },
              ),
              const Divider(),
            ],
          ],
          const SizedBox(height: 28),
          Text(l.howTitle, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(l.howBody, style: const TextStyle(color: Brand.ink2)),
          const SizedBox(height: 16),
          Text(
            l.materialsIncluded,
            style: const TextStyle(
              color: Brand.green700,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _BookingsTab extends StatefulWidget {
  final VoidCallback onBook;
  final ValueChanged<BookingSummary> onDetail;
  const _BookingsTab({super.key, required this.onBook, required this.onDetail});
  @override
  State<_BookingsTab> createState() => _BookingsTabState();
}

class _BookingsTabState extends State<_BookingsTab> {
  List<BookingSummary>? _bookings;
  Object? _error;
  final _refresh = RefreshGate();
  int _filter = 0;
  @override
  void initState() {
    super.initState();
    reload();
  }

  Future<void> reload() => _refresh.run(() async {
    try {
      final data = await context.read<Repository>().bookings('all');
      if (mounted) {
        setState(() {
          _bookings = data;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  });

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final filtered = (_bookings ?? [])
        .where(
          (b) =>
              _filter == 0 ||
              (_filter == 1
                  ? liveStatuses.contains(b.status) || b.status == 'DISPUTED'
                  : !liveStatuses.contains(b.status) && b.status != 'DISPUTED'),
        )
        .toList();
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
        itemCount: filtered.length + 1,
        itemBuilder: (context, index) {
          if (index > 0) {
            return Column(
              children: [
                BookingTile(
                  booking: filtered[index - 1],
                  onTap: () => widget.onDetail(filtered[index - 1]),
                ),
                const Divider(),
              ],
            );
          }
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                l.bookings,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                children: [
                  for (final (i, label) in [
                    l.allBookings,
                    l.upcoming,
                    l.pastBookings,
                  ].indexed)
                    ChoiceChip(
                      label: Text(label),
                      selected: _filter == i,
                      onSelected: (_) => setState(() => _filter = i),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              if (_error != null) ErrorRetry(error: _error!, onRetry: reload),
              if (_bookings == null && _error == null)
                LoadingState(l.loadingBookings),
              if (_bookings != null && filtered.isEmpty)
                EmptyState(
                  icon: Icons.receipt_long_outlined,
                  title: l.noFilteredBookings,
                  body: l.noFilteredBody,
                  action: OutlinedButton(
                    onPressed: widget.onBook,
                    child: Text(l.bookCleaning),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class BookingTile extends StatelessWidget {
  final BookingSummary booking;
  final VoidCallback onTap;
  final bool padded;
  const BookingTile({
    super.key,
    required this.booking,
    required this.onTap,
    this.padded = true,
  });
  @override
  Widget build(BuildContext context) {
    final lang = Localizations.localeOf(context).languageCode;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(Brand.radius),
      child: Padding(
        padding: EdgeInsets.symmetric(vertical: padded ? 18 : 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ServiceBadge(booking.serviceIcon, size: 40),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        booking.serviceName(lang),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${formatDate(context, booking.date)} · ${booking.startTime}',
                        style: const TextStyle(color: Brand.ink3),
                      ),
                      Text(
                        booking.areaName,
                        style: const TextStyle(color: Brand.ink3),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right, size: 20, color: Brand.ink3),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                StatusChip(booking.status),
                Text(
                  formatMoney(booking.total, booking.currency),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab();
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final state = context.watch<AppState>();
    final me = state.me;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
      children: [
        Text(l.profile, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 24),
        Text(me?.fullName ?? '', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        Text(
          [me?.phone, me?.email].whereType<String>().join('\n'),
          style: const TextStyle(color: Brand.ink3),
        ),
        const SizedBox(height: 28),
        const Divider(),
        const SizedBox(height: 24),
        Text(l.language, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerLeft,
          child: LanguageToggle(
            value: state.locale,
            onChanged: state.setLocale,
          ),
        ),
        const SizedBox(height: 24),
        const Divider(),
        const SizedBox(height: 12),
        TextButton.icon(
          onPressed: () => showSupportSheet(context),
          icon: const Icon(Icons.help_outline),
          label: Text(l.contactSupport),
        ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: () async {
            final logout = await showDialog<bool>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: Text(l.signOutConfirm),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx, false),
                    child: Text(l.staySignedIn),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pop(ctx, true),
                    child: Text(l.signOut),
                  ),
                ],
              ),
            );
            if (logout == true) await state.logout();
          },
          icon: const Icon(Icons.logout),
          label: Text(l.signOut),
        ),
      ],
    );
  }
}
