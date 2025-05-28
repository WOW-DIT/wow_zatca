// Copyright (c) 2025, WOWDIT and contributors
// For license information, please see license.txt

frappe.ui.form.on('EGSUnit', {
	refresh: function(frm) {
		const status = frm.doc.status;

		if(status === "Pending") {
			frm.add_custom_button('Issue Production Certificate', () => {
				frappe.show_progress(__('Onboarding EGS Unit'), 0, 100, "Progress Started");
				fullOnboarding(frm);
			}, 'Issue Production Certificate');

			// frm.add_custom_button('Issue Compliance Certificate', () => {
			// 	compliance_csid(frm);
			// }, 'Issue Compliance Certificate');

		} else if(status === "Requested") {
			frm.add_custom_button('Check Compliance', () => {
				checkInvoices(frm);
			}, 'Check Compliance');

		} else if(status === "Compliance") {
			frm.add_custom_button('Issue Production Certificate', () => {
				productionCertificate(frm);
			}, 'Issue Production Certificate');

		} else if(status === "Production") {
			frm.add_custom_button('Renew Certificate', () => {
				renewCertificate(frm);
			}, 'Post Production');
		}
	}
});


function fullOnboarding(frm) {
	frappe.realtime.on("unit_onboarding_progress", function (data) {
		frappe.show_progress(__('Onboarding EGS Unit'), data.percent, 100, data.message);
		if (data.step === "done") {
			frappe.show_alert({message: "EGS Unit onboarded successfully ✅", indicator: 'green'});
			frappe.hide_progress();
			location.reload();
		}
		if (data.step === "error" || data.step === "failed") {
			frappe.show_alert({message: data.message, indicator: 'red'});
		}
	});

	const otp = prompt("Enter the OTP");
	if(otp) {
		frappe.call({
			method: "zatca.api_onboarding.unit_onboarding_task",
			args: {
				"docname": frm.doc.name,
				"otp": otp,
				"auto_check": true,
			},
			callback: function(res) {
			}
		})
	}
}


function compliance_csid(frm) {
	frappe.realtime.on("unit_onboarding_progress", function (data) {
		frappe.show_progress(__('Onboarding EGS Unit'), data.percent, 100, data.message);
		if (data.step === "done") {
			frappe.show_alert({message: "EGS Unit onboarded successfully ✅", indicator: 'green'});
			frappe.hide_progress();
			location.reload();
		}
		if (data.step === "error" || data.step === "failed") {
			frappe.show_alert({message: data.message, indicator: 'red'});
		}
	});
	const otp = prompt("Enter the OTP");
	if(otp) {
		frappe.call({
			method: "zatca.api_onboarding.unit_onboarding_task",
			args: {
				"docname": frm.doc.name,
				"otp": otp,
				"auto_check": false,
			},
			callback: function(res) {
				console.log(res)
			}
		})
	}
}


function checkInvoices(frm) {
	frappe.realtime.on("check_invoices_progress", function (data) {
		frappe.show_progress(__('Checking Compliance'), data.percent, 100, data.message);
		if (data.step === "done") {
			frappe.show_alert({message: "Production Certificate is ready to be issued ✅", indicator: 'green'});
			// frappe.hide_progress();
			// location.reload();
		}
		if (data.step === "partialy_done") {
			frappe.show_alert({message: "Compliance Certificate is saved ✅", indicator: 'green'});
			frm.reload_doc();
		}
		if (data.step === "error" || data.step === "failed") {
			frappe.show_alert({message: data.message, indicator: 'red'});
		}
	});

	frappe.call({
		method: "zatca.api_onboarding.check_invoices_task",
		args: {
			"docname": frm.doc.name,
		},
		callback: function(res) {
		}
	})
}


function productionCertificate(frm) {
	frappe.realtime.on("production_progress", function (data) {
		frappe.show_progress(__('Issuing Production Certificate'), data.percent, 100, data.message);
		if (data.step === "done") {
			frappe.show_alert({message: "EGS Unit is production ready ✅", indicator: 'green'});
			frappe.hide_progress();
			location.reload();
		}
		if (data.step === "error" || data.step === "failed") {
			frappe.show_alert({message: data.message, indicator: 'red'});
		}
	});
	console.log("ASDSADSADKMAS")

	frappe.call({
		method: "zatca.api_onboarding.issue_production_cert_task",
		args: {
			"docname": frm.doc.name,
		},
		callback: function(res) {

		}
	})
}


function renewCertificate(frm) {
	frappe.realtime.on("rewnew_unit_onboarding_progress", function (data) {
		frappe.show_progress(__('Renewing Certificate'), 100, 100, data.message);
		if (data.step === "done") {
			frappe.show_alert({message: "Certificate has been renewed successfully ✅", indicator: 'green'});
			frappe.hide_progress();
			location.reload();
		}
		if (data.step === "error" || data.step === "failed") {
			frappe.show_alert({message: data.message, indicator: 'red'});
		}
	});

	const otp = prompt("Enter the OTP");
	if(otp) {
		frappe.call({
			method: "zatca.api_onboarding.renew_unit_onboarding_task",
			args: {
				"docname": frm.doc.name,
				"otp": otp,
			},
			callback: function(res) {
			}
		})
	}
}