import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/config.dart';
import '../../l10n/app_localizations.dart';
import '../../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/editorial_photo.dart';

class _Introduction {
  final String photo;
  final String title;
  final String body;
  final String photoLabel;
  const _Introduction(this.photo, this.title, this.body, this.photoLabel);

  static List<_Introduction> pages(AppLocalizations l) => [
    _Introduction(
      EditorialImages.brightHome,
      l.onboardingOutcomeTitle,
      l.onboardingOutcomeBody,
      l.brightHomePhotoAlt,
    ),
    _Introduction(
      EditorialImages.workspace,
      l.onboardingProfessionalTitle,
      l.onboardingProfessionalBody,
      l.professionalPhotoAlt,
    ),
    _Introduction(
      EditorialImages.peacefulHome,
      l.onboardingPeaceTitle,
      l.onboardingPeaceBody,
      l.peaceHomePhotoAlt,
    ),
  ];
}

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});
  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;
  bool _finishing = false;
  bool _cached = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_cached) return;
    _cached = true;
    // Only the opening photograph and its neighbour, with a bounded decode.
    precacheImage(
      EditorialImages.provider(EditorialImages.brightHome),
      context,
    );
    precacheImage(EditorialImages.provider(EditorialImages.workspace), context);
  }

  Future<void> _finish() async {
    if (_finishing) return;
    setState(() => _finishing = true);
    await context.read<AppState>().completeOnboarding();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final state = context.watch<AppState>();
    final pages = _Introduction.pages(l);
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 8, 16, 8),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      AppConfig.appName,
                      style: TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.w700,
                        color: Brand.green900,
                      ),
                    ),
                  ),
                  if (_page < 2)
                    TextButton(
                      key: const ValueKey('onboarding-skip'),
                      onPressed: _finishing ? null : _finish,
                      child: Text(l.onboardingSkip),
                    ),
                ],
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: pages.length,
                onPageChanged: (page) {
                  setState(() => _page = page);
                  if (page == 1) {
                    precacheImage(
                      EditorialImages.provider(EditorialImages.peacefulHome),
                      context,
                    );
                  }
                },
                itemBuilder: (_, index) => LayoutBuilder(
                  builder: (_, box) {
                    final content = pages[index];
                    return SingleChildScrollView(
                      key: ValueKey('onboarding-page-$index'),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          EditorialPhoto(
                            asset: content.photo,
                            label: content.photoLabel,
                            height: (box.maxHeight * .53).clamp(180, 380),
                          ),
                          Padding(
                            padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  content.title,
                                  style: const TextStyle(
                                    fontSize: 32,
                                    height: 1.12,
                                    letterSpacing: -.8,
                                    fontWeight: FontWeight.w600,
                                    color: Brand.green900,
                                  ),
                                ),
                                const SizedBox(height: 14),
                                Text(
                                  content.body,
                                  style: const TextStyle(
                                    fontSize: 15,
                                    height: 1.55,
                                    color: Brand.ink2,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Semantics(
                        label: '${_page + 1} / 3',
                        child: Row(
                          children: List.generate(
                            3,
                            (index) => Container(
                              margin: const EdgeInsets.only(right: 6),
                              width: index == _page ? 24 : 6,
                              height: 6,
                              decoration: BoxDecoration(
                                color: index == _page
                                    ? Brand.green700
                                    : Brand.line,
                                borderRadius: BorderRadius.circular(4),
                              ),
                            ),
                          ),
                        ),
                      ),
                      LanguageToggle(
                        value: state.locale,
                        onChanged: (locale) =>
                            state.setLocale(locale, persistRemote: false),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  FilledButton(
                    key: const ValueKey('onboarding-next'),
                    onPressed: _finishing
                        ? null
                        : () {
                            if (_page == 2) {
                              _finish();
                            } else {
                              _controller.nextPage(
                                duration: const Duration(milliseconds: 260),
                                curve: Curves.easeOutCubic,
                              );
                            }
                          },
                    child: Text(
                      _page == 2 ? l.onboardingStart : l.onboardingNext,
                    ),
                  ),
                  if (_page == 2)
                    TextButton(
                      key: const ValueKey('onboarding-sign-in'),
                      onPressed: _finishing ? null : _finish,
                      child: Text(
                        l.onboardingSignIn,
                        textAlign: TextAlign.center,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
