/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 Eric Neuman
 *
 * tmag5273_nub.c — TI TMAG5273 I2C 3D hall sensor as a ThinkPad-style
 * rate-control pointing nub (the v0.21 "Bean-style" pointer: magnet in a
 * printed flexure spring above the sensor, architecture per the Ploopy Bean,
 * CERN-OHL-S v2 hardware; this driver is an original work referencing the
 * Apache-2.0 upstream Zephyr tmag5273 sensor driver for the register map and
 * the TI datasheet SLYS045 for field semantics).
 *
 * Behaviour: at boot the magnetic zero is averaged over calib-samples polls
 * (this also swallows the MagSafe ring's static ambient field ~90mm away).
 * Each poll reads X/Y field, subtracts the zero, applies a deadzone, and maps
 * the excess through a QUADRATIC curve to pointer velocity — deflection angle
 * controls cursor SPEED (true trackpoint rate control), with fixed-point
 * remainder accumulation so slow precise motion still creeps sub-pixel.
 */

#define DT_DRV_COMPAT thumbdeck_tmag5273_nub

#include <zephyr/device.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/input/input.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/pm/device.h>

LOG_MODULE_REGISTER(tmag5273_nub, CONFIG_INPUT_LOG_LEVEL);

/* Register map (TI TMAG5273 datasheet; matches upstream Zephyr driver) */
#define TMAG_REG_DEVICE_CONFIG_1  0x00
#define TMAG_REG_DEVICE_CONFIG_2  0x01
#define TMAG_REG_SENSOR_CONFIG_1  0x02
#define TMAG_REG_SENSOR_CONFIG_2  0x03
#define TMAG_REG_MANUFACTURER_LSB 0x0E
#define TMAG_REG_X_MSB_RESULT     0x12
#define TMAG_REG_CONV_STATUS      0x18

#define TMAG_MANUFACTURER_ID      0x5449 /* "TI" */

/* DEVICE_CONFIG_1: CRC off, 8x conversion averaging, standard I2C reads.
 * v0.26 also selects MAG_TEMPCO = 01b (bits [6:5]) = 0.12%/degC, the NdFeB
 * coefficient. The magnet IS NdFeB and loses ~0.12%/degC of remanence, so
 * leaving this at "no compensation" let the pointer gain drift with hand and
 * ambient temperature. It is a free register field. */
#define TMAG_CONV_AVG_8           (3u << 2)
#define TMAG_TEMPCO_NDFEB         (1u << 5)
/* SENSOR_CONFIG_1[7:4] MAG_CH_EN: 0x3 = X and Y channels */
#define TMAG_MAG_CH_EN_XY         (0x3u << 4)
/* SENSOR_CONFIG_2 bit1: X/Y range. 0 = +/-40mT (the A1 reset default), 1 = +/-80mT.
 *
 * v0.26 uses the +/-40mT range, i.e. this bit is left CLEAR. The old code set it
 * and justified it as "headroom vs the close nub magnet" — but that conflates the
 * AXIAL field with the channels actually being measured. MAG_CH_EN above enables
 * X and Y only; Z is never converted, so the ~52mT sitting on the magnet's axis
 * never enters a measured channel. X/Y only ever see the TRANSVERSE field, which is
 * the tilt signal (<= ~4.3mT even at a 320gf abuse push) plus the static offset from
 * the die's 0.418mm in-package misalignment (~6.7mT). Worst case is under 12mT — 30%
 * of the +/-40mT scale — so the wider range bought nothing and cost half the
 * resolution. At +/-40mT a count is 1.2207uT instead of 2.4414uT. */
/* DEVICE_CONFIG_2[1:0] operating mode: 1 = sleep, 2 = continuous measure */
#define TMAG_OP_MODE_SLEEP        0x1u
#define TMAG_OP_MODE_CONTINUOUS   0x2u

struct nub_config {
	struct i2c_dt_spec i2c;
	uint32_t sampling_hz;
	int32_t deadzone;
	int32_t gain_num;
	int32_t gain_div;
	int32_t max_out;
	uint32_t calib_samples;
	bool invert_x;
	bool invert_y;
	bool swap_xy;
};

struct nub_data {
	const struct device *dev;
	struct k_work_delayable work;
	int32_t zero_x, zero_y;
	int64_t calib_acc_x, calib_acc_y;
	uint32_t calib_left;
	int32_t rem_x, rem_y; /* 1/256-px velocity remainders */
};

static int nub_read_xy(const struct device *dev, int16_t *x, int16_t *y)
{
	const struct nub_config *cfg = dev->config;
	uint8_t buf[4];
	int ret;

	/* X_MSB..Y_LSB are contiguous (0x12..0x15), MSB first */
	ret = i2c_burst_read_dt(&cfg->i2c, TMAG_REG_X_MSB_RESULT, buf, sizeof(buf));
	if (ret < 0) {
		return ret;
	}
	*x = (int16_t)((buf[0] << 8) | buf[1]);
	*y = (int16_t)((buf[2] << 8) | buf[3]);
	return 0;
}

/* quadratic rate curve: velocity_256 = excess^2 * gain_num / gain_div,
 * clamped to max_out pixels/poll, sign restored, remainder-accumulated */
static int32_t nub_curve(const struct nub_config *cfg, int32_t d, int32_t *rem)
{
	int32_t mag = d < 0 ? -d : d;
	int32_t out;

	if (mag <= cfg->deadzone) {
		return 0;
	}
	mag -= cfg->deadzone;

	int64_t v256 = ((int64_t)mag * mag * cfg->gain_num) / cfg->gain_div;
	int64_t vmax = (int64_t)cfg->max_out * 256;

	if (v256 > vmax) {
		v256 = vmax;
	}
	*rem += (d < 0) ? -(int32_t)v256 : (int32_t)v256;
	out = *rem / 256;
	*rem -= out * 256;
	return out;
}

static void nub_work_handler(struct k_work *work)
{
	struct k_work_delayable *dwork = k_work_delayable_from_work(work);
	struct nub_data *data = CONTAINER_OF(dwork, struct nub_data, work);
	const struct device *dev = data->dev;
	const struct nub_config *cfg = dev->config;
	int16_t raw_x, raw_y;

	if (nub_read_xy(dev, &raw_x, &raw_y) == 0) {
		if (data->calib_left > 0) {
			/* boot zero calibration (also swallows ambient field) */
			data->calib_acc_x += raw_x;
			data->calib_acc_y += raw_y;
			data->calib_left--;
			if (data->calib_left == 0) {
				data->zero_x = (int32_t)(data->calib_acc_x /
							 cfg->calib_samples);
				data->zero_y = (int32_t)(data->calib_acc_y /
							 cfg->calib_samples);
				LOG_INF("nub zero: x=%d y=%d", data->zero_x,
					data->zero_y);
			}
		} else {
			int32_t dx = (int32_t)raw_x - data->zero_x;
			int32_t dy = (int32_t)raw_y - data->zero_y;

			if (cfg->swap_xy) {
				int32_t t = dx;
				dx = dy;
				dy = t;
			}
			if (cfg->invert_x) {
				dx = -dx;
			}
			if (cfg->invert_y) {
				dy = -dy;
			}

			int32_t rx = nub_curve(cfg, dx, &data->rem_x);
			int32_t ry = nub_curve(cfg, dy, &data->rem_y);

			if (rx != 0) {
				input_report_rel(dev, INPUT_REL_X, rx,
						 ry == 0, K_NO_WAIT);
			}
			if (ry != 0) {
				input_report_rel(dev, INPUT_REL_Y, ry, true,
						 K_NO_WAIT);
			}
		}
	}

	k_work_schedule(&data->work, K_MSEC(1000U / cfg->sampling_hz));
}

static int nub_configure(const struct device *dev)
{
	const struct nub_config *cfg = dev->config;
	int ret;

	ret = i2c_reg_write_byte_dt(&cfg->i2c, TMAG_REG_DEVICE_CONFIG_1,
				    TMAG_CONV_AVG_8 | TMAG_TEMPCO_NDFEB);
	if (ret == 0) {
		ret = i2c_reg_write_byte_dt(&cfg->i2c, TMAG_REG_SENSOR_CONFIG_1,
					    TMAG_MAG_CH_EN_XY);
	}
	if (ret == 0) {
		/* X/Y range stays at the +/-40mT reset default (bit 1 clear) — see the
		 * SENSOR_CONFIG_2 comment above for why the wider range was wrong. */
		ret = i2c_reg_write_byte_dt(&cfg->i2c, TMAG_REG_SENSOR_CONFIG_2, 0x00);
	}
	if (ret == 0) {
		ret = i2c_reg_write_byte_dt(&cfg->i2c, TMAG_REG_DEVICE_CONFIG_2,
					    TMAG_OP_MODE_CONTINUOUS);
	}
	return ret;
}

#ifdef CONFIG_PM_DEVICE
/* ZMK deep sleep (CONFIG_ZMK_SLEEP) suspends devices on the way into
 * SOFT_OFF. Without this hook the sensor free-runs conversions at ~2.3 mA
 * forever — REG0/3V3 stays up in System OFF — draining the 403040 cell in
 * ~a week while the deck "sleeps". Sleep mode is ~5 nA typ. The nub cannot
 * wake the deck (INT is wired but unused); any matrix key wakes it, and
 * RESUME re-runs the zero calibration since the boot ambient may have moved. */
static int nub_pm_action(const struct device *dev, enum pm_device_action action)
{
	const struct nub_config *cfg = dev->config;
	struct nub_data *data = dev->data;

	switch (action) {
	case PM_DEVICE_ACTION_SUSPEND:
		k_work_cancel_delayable(&data->work);
		return i2c_reg_write_byte_dt(&cfg->i2c, TMAG_REG_DEVICE_CONFIG_2,
					     TMAG_OP_MODE_SLEEP);
	case PM_DEVICE_ACTION_RESUME: {
		int ret = nub_configure(dev);

		if (ret < 0) {
			return ret;
		}
		data->calib_left = cfg->calib_samples;
		data->calib_acc_x = data->calib_acc_y = 0;
		data->rem_x = data->rem_y = 0;
		k_work_schedule(&data->work, K_MSEC(50));
		return 0;
	}
	default:
		return -ENOTSUP;
	}
}
#endif /* CONFIG_PM_DEVICE */

static int nub_init(const struct device *dev)
{
	const struct nub_config *cfg = dev->config;
	struct nub_data *data = dev->data;
	uint8_t id[2];
	int ret;

	if (!i2c_is_ready_dt(&cfg->i2c)) {
		LOG_ERR("I2C bus not ready");
		return -ENODEV;
	}

	ret = i2c_burst_read_dt(&cfg->i2c, TMAG_REG_MANUFACTURER_LSB, id, 2);
	if (ret < 0) {
		LOG_ERR("manufacturer id read failed (%d)", ret);
		return ret;
	}
	if (((id[1] << 8) | id[0]) != TMAG_MANUFACTURER_ID) {
		LOG_ERR("not a TMAG5273 (id 0x%02x%02x)", id[1], id[0]);
		return -ENODEV;
	}

	ret = nub_configure(dev);
	if (ret < 0) {
		LOG_ERR("sensor config failed (%d)", ret);
		return ret;
	}

	data->dev = dev;
	data->calib_left = cfg->calib_samples;
	k_work_init_delayable(&data->work, nub_work_handler);
	k_work_schedule(&data->work, K_MSEC(50)); /* let the supply settle */

	LOG_INF("TMAG5273 nub up (%u Hz, dz %d, gain %d/%d, max %d px)",
		cfg->sampling_hz, cfg->deadzone, cfg->gain_num, cfg->gain_div,
		cfg->max_out);
	return 0;
}

#define NUB_INIT(inst)                                                         \
	static const struct nub_config nub_config_##inst = {                   \
		.i2c = I2C_DT_SPEC_INST_GET(inst),                             \
		.sampling_hz = DT_INST_PROP(inst, sampling_hz),                \
		.deadzone = DT_INST_PROP(inst, deadzone),                      \
		.gain_num = DT_INST_PROP(inst, gain_num),                      \
		.gain_div = DT_INST_PROP(inst, gain_div),                      \
		.max_out = DT_INST_PROP(inst, max_out),                        \
		.calib_samples = DT_INST_PROP(inst, calib_samples),            \
		.invert_x = DT_INST_PROP(inst, invert_x),                      \
		.invert_y = DT_INST_PROP(inst, invert_y),                      \
		.swap_xy = DT_INST_PROP(inst, swap_xy),                        \
	};                                                                     \
	static struct nub_data nub_data_##inst;                                \
	PM_DEVICE_DT_INST_DEFINE(inst, nub_pm_action);                         \
	DEVICE_DT_INST_DEFINE(inst, nub_init, PM_DEVICE_DT_INST_GET(inst),     \
			      &nub_data_##inst, &nub_config_##inst,            \
			      POST_KERNEL, CONFIG_INPUT_INIT_PRIORITY, NULL);

DT_INST_FOREACH_STATUS_OKAY(NUB_INIT)
