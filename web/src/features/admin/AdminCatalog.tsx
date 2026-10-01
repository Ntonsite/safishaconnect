import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";
import { adminApi } from "../../api/endpoints";
import type { OptionGroup, Service, ServiceOption } from "../../api/types";
import { ServiceIcon } from "../../shared/components/Brand";
import { Button } from "../../shared/components/Button";
import { PageHeader } from "../../shared/components/Controls";
import { ErrorState, PageLoader } from "../../shared/components/Feedback";
import { Field, Input, Select, Switch, Textarea } from "../../shared/components/Field";
import { Modal } from "../../shared/components/Modal";
import { useToast } from "../../shared/components/Toast";
import { useFormat } from "../../shared/hooks/useFormat";

type ServiceForm = Pick<
  Service,
  | "slug"
  | "name_en"
  | "name_sw"
  | "summary_en"
  | "summary_sw"
  | "description_en"
  | "description_sw"
  | "icon"
  | "is_active"
  | "display_order"
  | "base_price"
  | "base_duration_minutes"
  | "uses_rooms"
  | "included_bedrooms"
  | "included_bathrooms"
  | "price_per_extra_bedroom"
  | "price_per_extra_bathroom"
  | "minutes_per_extra_room"
  | "max_rooms"
>;

const EMPTY_SERVICE: ServiceForm = {
  slug: "",
  name_en: "",
  name_sw: "",
  summary_en: "",
  summary_sw: "",
  description_en: "",
  description_sw: "",
  icon: "sparkles",
  is_active: true,
  display_order: 10,
  base_price: "0",
  base_duration_minutes: 120,
  uses_rooms: true,
  included_bedrooms: 1,
  included_bathrooms: 1,
  price_per_extra_bedroom: "0",
  price_per_extra_bathroom: "0",
  minutes_per_extra_room: 0,
  max_rooms: 8,
};

function useAdminSaved(key: string[]) {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  return {
    onSuccess: () => {
      toast.success(t("common.saved"));
      void qc.invalidateQueries({ queryKey: key });
      void qc.invalidateQueries({ queryKey: ["services"] });
      void qc.invalidateQueries({ queryKey: ["areas"] });
    },
    onError: toast.error,
  };
}

export function AdminServicesPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const query = useQuery({ queryKey: ["admin", "services"], queryFn: adminApi.services });
  const [editing, setEditing] = useState<Service | "new" | null>(null);
  const [optionFor, setOptionFor] = useState<{ service: Service; option?: ServiceOption } | null>(null);

  if (query.isLoading) return <PageLoader />;
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;

  return (
    <div className="stack-lg">
      <PageHeader
        title={t("nav.admin.services")}
        actions={
          <Button icon={<Plus />} onClick={() => setEditing("new")}>
            {t("admin.service.new")}
          </Button>
        }
      />
      {query.data?.map((s) => (
        <section key={s.id} className="card stack" style={{ opacity: s.is_active ? 1 : 0.65 }}>
          <div className="row-between wrap">
            <div className="row">
              <ServiceIcon name={s.icon} />
              <div>
                <h2 className="card-title">
                  {fmt.pick(s, "name")} {!s.is_active && <span className="badge tone-slate">{t("common.inactive")}</span>}
                </h2>
                <div className="small muted">
                  {fmt.money(s.base_price)} · {fmt.duration(s.base_duration_minutes)}
                  {s.uses_rooms &&
                    ` · +${fmt.money(s.price_per_extra_bedroom)} / ${t("booking.bedrooms").toLowerCase()} · +${fmt.money(s.price_per_extra_bathroom)} / ${t("booking.bathrooms").toLowerCase()}`}
                </div>
              </div>
            </div>
            <div className="row">
              <Button size="sm" variant="secondary" icon={<Plus />} onClick={() => setOptionFor({ service: s })}>
                {t("admin.service.newOption")}
              </Button>
              <Button size="sm" variant="secondary" icon={<Pencil />} onClick={() => setEditing(s)}>
                {t("common.edit")}
              </Button>
            </div>
          </div>
          {s.options.length > 0 && (
            <div className="table-wrap" style={{ border: "1px solid var(--line)", borderRadius: "var(--radius)" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("admin.service.group")}</th>
                    <th>{t("admin.service.nameEn")}</th>
                    <th className="right">{t("admin.service.price")}</th>
                    <th className="right">{t("admin.service.extraMinutes")}</th>
                    <th>{t("common.status")}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {s.options.map((o) => (
                    <tr key={o.id}>
                      <td className="small muted">{t(`admin.service.groups.${o.group}`)}</td>
                      <td>
                        <div className="cell-main">{fmt.pick(o, "name")}</div>
                        <div className="cell-sub">
                          {o.code}
                          {o.max_quantity > 1 && ` · max ${o.max_quantity}`}
                        </div>
                      </td>
                      <td className="right num">{fmt.money(o.price_amount)}</td>
                      <td className="right num">{o.duration_minutes}</td>
                      <td>
                        <span className={`badge ${o.is_active ? "tone-green" : "tone-slate"}`}>
                          {o.is_active ? t("common.active") : t("common.inactive")}
                        </span>
                      </td>
                      <td className="right">
                        <button className="icon-btn" aria-label={t("common.edit")} onClick={() => setOptionFor({ service: s, option: o })}>
                          <Pencil size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ))}
      <ServiceDialog service={editing} onClose={() => setEditing(null)} />
      <OptionDialog target={optionFor} onClose={() => setOptionFor(null)} />
    </div>
  );
}

function ServiceDialog({ service, onClose }: { service: Service | "new" | null; onClose: () => void }) {
  const { t } = useTranslation();
  const [form, setForm] = useState<ServiceForm>(EMPTY_SERVICE);
  const isNew = service === "new";
  useEffect(() => {
    if (service === "new") setForm(EMPTY_SERVICE);
    else if (service) {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { id, options, ...rest } = service;
      setForm(rest);
    }
  }, [service]);
  const saved = useAdminSaved(["admin", "services"]);
  const save = useMutation({
    mutationFn: () => {
      if (isNew) return adminApi.createService(form);
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { slug, ...patch } = form;
      return adminApi.updateService((service as Service).id, patch);
    },
    ...saved,
    onSuccess: () => {
      saved.onSuccess();
      onClose();
    },
  });
  const set = <K extends keyof ServiceForm>(k: K, v: ServiceForm[K]) => setForm((f) => ({ ...f, [k]: v }));
  const num = (k: keyof ServiceForm) => (e: React.ChangeEvent<HTMLInputElement>) => set(k, Number(e.target.value) as never);
  const money = (k: keyof ServiceForm) => (e: React.ChangeEvent<HTMLInputElement>) => set(k, e.target.value as never);

  return (
    <Modal
      open={!!service}
      wide
      title={isNew ? t("admin.service.new") : t("admin.service.edit")}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button loading={save.isPending} onClick={() => save.mutate()}>
            {t("common.save")}
          </Button>
        </>
      }
    >
      <div className="stack">
        <div className="grid-2">
          <Field label={t("admin.service.nameEn")}>
            <Input value={form.name_en} onChange={(e) => set("name_en", e.target.value)} />
          </Field>
          <Field label={t("admin.service.nameSw")}>
            <Input value={form.name_sw} onChange={(e) => set("name_sw", e.target.value)} />
          </Field>
          {isNew && (
            <Field label={t("admin.service.slug")} hint="window-cleaning">
              <Input value={form.slug} onChange={(e) => set("slug", e.target.value.toLowerCase())} />
            </Field>
          )}
          <Field label={t("admin.service.icon")}>
            <Select value={form.icon} onChange={(e) => set("icon", e.target.value)}>
              {["sparkles", "home", "building", "truck", "sofa"].map((i) => (
                <option key={i}>{i}</option>
              ))}
            </Select>
          </Field>
          <Field label={t("admin.service.summaryEn")}>
            <Input value={form.summary_en} onChange={(e) => set("summary_en", e.target.value)} maxLength={255} />
          </Field>
          <Field label={t("admin.service.summarySw")}>
            <Input value={form.summary_sw} onChange={(e) => set("summary_sw", e.target.value)} maxLength={255} />
          </Field>
          <Field label={t("admin.service.descriptionEn")}>
            <Textarea value={form.description_en} onChange={(e) => set("description_en", e.target.value)} rows={3} />
          </Field>
          <Field label={t("admin.service.descriptionSw")}>
            <Textarea value={form.description_sw} onChange={(e) => set("description_sw", e.target.value)} rows={3} />
          </Field>
          <Field label={t("admin.service.basePrice")}>
            <Input type="number" min={0} step={500} value={form.base_price} onChange={money("base_price")} />
          </Field>
          <Field label={t("admin.service.baseDuration")}>
            <Input type="number" min={15} step={15} value={form.base_duration_minutes} onChange={num("base_duration_minutes")} />
          </Field>
        </div>
        <Switch checked={form.uses_rooms} onChange={(v) => set("uses_rooms", v)} label={t("admin.service.usesRooms")} />
        {form.uses_rooms && (
          <div className="grid-3">
            <Field label={t("admin.service.includedBedrooms")}>
              <Input type="number" min={0} value={form.included_bedrooms} onChange={num("included_bedrooms")} />
            </Field>
            <Field label={t("admin.service.extraBedroom")}>
              <Input type="number" min={0} step={500} value={form.price_per_extra_bedroom} onChange={money("price_per_extra_bedroom")} />
            </Field>
            <Field label={t("admin.service.minutesPerRoom")}>
              <Input type="number" min={0} value={form.minutes_per_extra_room} onChange={num("minutes_per_extra_room")} />
            </Field>
            <Field label={t("admin.service.includedBathrooms")}>
              <Input type="number" min={0} value={form.included_bathrooms} onChange={num("included_bathrooms")} />
            </Field>
            <Field label={t("admin.service.extraBathroom")}>
              <Input type="number" min={0} step={500} value={form.price_per_extra_bathroom} onChange={money("price_per_extra_bathroom")} />
            </Field>
          </div>
        )}
        <div className="row wrap" style={{ gap: "var(--s-6)" }}>
          <Field label={t("admin.service.displayOrder")}>
            <Input type="number" value={form.display_order} onChange={num("display_order")} style={{ width: 120 }} />
          </Field>
          <Switch checked={form.is_active} onChange={(v) => set("is_active", v)} label={t("common.active")} />
        </div>
      </div>
    </Modal>
  );
}

function OptionDialog({ target, onClose }: { target: { service: Service; option?: ServiceOption } | null; onClose: () => void }) {
  const { t } = useTranslation();
  const blank = { group: "ADDON" as OptionGroup, code: "", name_en: "", name_sw: "", price_amount: "0", duration_minutes: 0, max_quantity: 1, is_active: true, display_order: 50 };
  const [form, setForm] = useState(blank);
  useEffect(() => {
    if (target?.option) {
      const o = target.option;
      setForm({ group: o.group, code: o.code, name_en: o.name_en, name_sw: o.name_sw, price_amount: o.price_amount, duration_minutes: o.duration_minutes, max_quantity: o.max_quantity, is_active: o.is_active, display_order: o.display_order });
    } else if (target) setForm(blank);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);
  const saved = useAdminSaved(["admin", "services"]);
  const save = useMutation({
    mutationFn: () => {
      if (target?.option) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { group, code, ...patch } = form;
        return adminApi.updateOption(target.option.id, patch);
      }
      return adminApi.createOption(target!.service.id, form);
    },
    ...saved,
    onSuccess: () => {
      saved.onSuccess();
      onClose();
    },
  });
  const isNew = !target?.option;
  return (
    <Modal
      open={!!target}
      title={isNew ? t("admin.service.newOption") : t("common.edit")}
      description={target?.service.name_en}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button loading={save.isPending} onClick={() => save.mutate()}>
            {t("common.save")}
          </Button>
        </>
      }
    >
      <div className="grid-2">
        {isNew && (
          <>
            <Field label={t("admin.service.group")}>
              <Select value={form.group} onChange={(e) => setForm({ ...form, group: e.target.value as OptionGroup })}>
                {(["PROPERTY_TYPE", "SIZE", "ADDON"] as const).map((g) => (
                  <option key={g} value={g}>
                    {t(`admin.service.groups.${g}`)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t("admin.service.code")} hint="inside_fridge">
              <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toLowerCase() })} />
            </Field>
          </>
        )}
        <Field label={t("admin.service.nameEn")}>
          <Input value={form.name_en} onChange={(e) => setForm({ ...form, name_en: e.target.value })} />
        </Field>
        <Field label={t("admin.service.nameSw")}>
          <Input value={form.name_sw} onChange={(e) => setForm({ ...form, name_sw: e.target.value })} />
        </Field>
        <Field label={t("admin.service.price")}>
          <Input type="number" min={0} step={500} value={form.price_amount} onChange={(e) => setForm({ ...form, price_amount: e.target.value })} />
        </Field>
        <Field label={t("admin.service.extraMinutes")}>
          <Input type="number" min={0} value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} />
        </Field>
        <Field label={t("admin.service.maxQuantity")}>
          <Input type="number" min={1} value={form.max_quantity} onChange={(e) => setForm({ ...form, max_quantity: Number(e.target.value) })} />
        </Field>
        <div className="field" style={{ justifyContent: "flex-end" }}>
          <Switch checked={form.is_active} onChange={(v) => setForm({ ...form, is_active: v })} label={t("common.active")} />
        </div>
      </div>
    </Modal>
  );
}

export function AdminAreasPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const cities = useQuery({ queryKey: ["admin", "cities"], queryFn: adminApi.cities });
  const areas = useQuery({ queryKey: ["admin", "areas"], queryFn: adminApi.areas });
  const [cityId, setCityId] = useState("");
  const [name, setName] = useState("");
  const [cityName, setCityName] = useState("");
  const [region, setRegion] = useState("");
  useEffect(() => {
    if (!cityId && cities.data?.length) setCityId(cities.data[0].id);
  }, [cities.data, cityId]);
  const saved = useAdminSaved(["admin"]);
  const createArea = useMutation({
    mutationFn: () => adminApi.createArea({ city_id: cityId, name: name.trim() }),
    ...saved,
    onSuccess: () => {
      setName("");
      saved.onSuccess();
    },
  });
  const createCity = useMutation({
    mutationFn: () => adminApi.createCity({ name: cityName.trim(), region: region.trim() }),
    ...saved,
    onSuccess: () => {
      setCityName("");
      setRegion("");
      saved.onSuccess();
    },
  });
  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => adminApi.updateArea(id, { is_active: active }),
    ...saved,
    onError: toast.error,
  });

  if (cities.isLoading || areas.isLoading) return <PageLoader />;
  return (
    <div className="stack-lg">
      <PageHeader title={t("nav.admin.areas")} />
      <div className="grid-2">
        <form
          className="card stack"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim().length >= 2) createArea.mutate();
          }}
        >
          <h2 className="card-title">{t("admin.areas.new")}</h2>
          <Field label={t("admin.areas.city")}>
            <Select value={cityId} onChange={(e) => setCityId(e.target.value)}>
              {cities.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t("admin.areas.name")}>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <div>
            <Button type="submit" icon={<Plus />} loading={createArea.isPending} disabled={name.trim().length < 2}>
              {t("common.add")}
            </Button>
          </div>
        </form>
        <form
          className="card stack"
          onSubmit={(e) => {
            e.preventDefault();
            if (cityName.trim().length >= 2 && region.trim().length >= 2) createCity.mutate();
          }}
        >
          <h2 className="card-title">{t("admin.areas.newCity")}</h2>
          <Field label={t("admin.areas.city")}>
            <Input value={cityName} onChange={(e) => setCityName(e.target.value)} />
          </Field>
          <Field label={t("admin.areas.region")}>
            <Input value={region} onChange={(e) => setRegion(e.target.value)} />
          </Field>
          <div>
            <Button type="submit" variant="secondary" icon={<Plus />} loading={createCity.isPending}>
              {t("common.add")}
            </Button>
          </div>
        </form>
      </div>
      <div className="card card-flush">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>{t("admin.areas.name")}</th>
                <th>{t("admin.areas.city")}</th>
                <th>{t("common.status")}</th>
              </tr>
            </thead>
            <tbody>
              {areas.data?.map((a) => (
                <tr key={a.id}>
                  <td className="cell-main">{a.name}</td>
                  <td>{a.city_name}</td>
                  <td>
                    <Switch
                      checked={a.is_active}
                      onChange={(v) => toggle.mutate({ id: a.id, active: v })}
                      label={a.is_active ? t("common.active") : t("common.inactive")}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
